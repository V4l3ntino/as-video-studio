"""Cliente IPC del coordinador. Se copia/sella con cada paquete Blender nuevo.

El motor recibe PIL RGB real, por lo que conserva sus postprocesos y puede hacer
varios renders por frame. Solo el ejecutor inicia el proceso, antes de importar
el código del estilo. No usa sockets ni permite órdenes de subprocess del motor.
"""
import atexit
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

_sesion=None


class Sesion:
    def __init__(self,paquete,pedido):
        self.raiz=Path(pedido['salida']).resolve()/'blender'
        self.raiz.mkdir(parents=True,exist_ok=True)
        self.indice=0;self.cerrada=False;self.medidas=[];self.cola=queue.Queue()
        requirement=pedido['blender'];exe=Path(requirement['ejecutable'])
        with exe.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
        if sha!=requirement['sha256_ejecutable']:raise ValueError('el ejecutable Blender cambió antes de iniciarlo')
        server=(Path(paquete)/requirement['servidor']).resolve()
        if not server.is_relative_to(Path(paquete).resolve()) or not server.is_file():raise ValueError('falta el servidor Blender del paquete')
        config=dict(version=requirement['version'],ancho=pedido['ancho'],alto=pedido['alto'],fps=pedido['fps'],
            protocolo=1,samples=64)
        (self.raiz/'config.json').write_text(json.dumps(config),encoding='utf8')
        # Blender ignora PYTHON* sin --python-use-system-env. Se habilita solo
        # tras retirar rutas/configuración Python heredadas y vetar user-site.
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('PYTHON')}
        env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONSAFEPATH='1')
        for key,name in [('BLENDER_USER_CONFIG','config'),('BLENDER_USER_SCRIPTS','scripts'),
                ('BLENDER_USER_DATAFILES','data'),('TEMP','temp'),('TMP','temp')]:
            folder=self.raiz/'runtime'/name;folder.mkdir(parents=True,exist_ok=True);env[key]=str(folder)
        self.log=(self.raiz/'blender.log').open('wb')
        # CreateProcess de Windows rechaza cwd > MAX_PATH aunque Python pueda
        # abrir sus archivos. El intercambio sigue en salida; cwd es la caché
        # del paquete, no el runtime sellado ni el directorio del programa.
        cwd=Path(paquete).resolve()/'cache';cwd.mkdir(parents=True,exist_ok=True)
        self.proceso=subprocess.Popen([str(exe),'--background','--factory-startup','--disable-autoexec','--python-use-system-env',
            '--python-exit-code','1','--python',str(server),'--',str(self.raiz)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,cwd=str(cwd),env=env,
            text=True,encoding='utf8',errors='replace',bufsize=1)
        (self.raiz/'sesion.json').write_text(json.dumps(dict(pid=self.proceso.pid,
            coordinador=os.getpid(),ejecutable=str(exe),version=requirement['version'])),encoding='utf8')
        self.hilo=threading.Thread(target=self._leer,daemon=True);self.hilo.start()
        atexit.register(self.cerrar)
        try:
            self.info=self._respuesta(180)
            if self.info.get('estado')!='listo' or self.info.get('version')!=requirement['version']:
                raise ValueError('Blender no confirmó el runtime requerido: '+str(self.info))
        except BaseException:
            self.cerrar();raise

    def _leer(self):
        try:
            for line in self.proceso.stdout:
                if line.startswith('ESTUDIO_BLENDER '):
                    try:self.cola.put(json.loads(line[len('ESTUDIO_BLENDER '):]))
                    except ValueError:self.cola.put(dict(error='respuesta IPC Blender inválida'))
                else:
                    self.log.write(line.encode('utf8',errors='replace'));self.log.flush()
        finally:self.cola.put(None)

    def _respuesta(self,segundos):
        try:response=self.cola.get(timeout=segundos)
        except queue.Empty:
            self.cerrar();raise TimeoutError('Blender no respondió; se conservan sus entradas y log') from None
        if response is None:raise RuntimeError('Blender terminó sin respuesta; consultar '+str(self.raiz/'blender.log'))
        if response.get('error'):raise RuntimeError('Blender: '+response['error'])
        return response

    def render(self,w,h,mesh,cam,sprites,ambiente,volumen):
        import numpy as np
        from PIL import Image
        if self.cerrada:raise RuntimeError('la sesión Blender ya está cerrada')
        if not(16<=w<=4096 and 16<=h<=4096):raise ValueError('resolución Blender no permitida')
        folder=self.raiz/'intercambio'/f'{self.indice:06}';folder.mkdir(parents=True,exist_ok=False)
        self.indice+=1
        data=np.asarray(mesh.vertices,dtype='f4').reshape(-1,10)
        np.save(folder/'malla.npy',data,allow_pickle=False)
        eye=np.asarray(cam['eye'],dtype='f8');target=np.asarray(cam['target'],dtype='f8');forward=target-eye
        right=np.cross(forward,(0,1,0));right/=max(float(np.linalg.norm(right)),1e-9)
        items=[]
        for i,item in enumerate(sprites):
            image,pos,height=item[:3];meta=item[3] if len(item)>3 else {}
            image.save(folder/f'actor_{i}.png')
            width=height*image.width/image.height;p=np.array(pos);bl=p-right*width/2;br=p+right*width/2
            items.append(dict(imagen=f'actor_{i}.png',vertices=np.asarray([bl,br,br+(0,height,0),bl+(0,height,0)]).tolist(),**meta))
        pedido=dict(ancho=w,alto=h,camara=cam,ambiente=ambiente or {},sprites=items,volumen=volumen)
        (folder/'escena.json').write_text(json.dumps(pedido,allow_nan=False),encoding='utf8')
        start=time.perf_counter()
        self.proceso.stdin.write(json.dumps(dict(render=folder.relative_to(self.raiz).as_posix()))+'\n');self.proceso.stdin.flush()
        response=self._respuesta(180)
        if response.get('render')!=folder.relative_to(self.raiz).as_posix():raise ValueError('Blender respondió a otra solicitud')
        with Image.open(folder/'frame.png') as source:frame=source.convert('RGB')
        depth=np.load(folder/'depth.npy',allow_pickle=False)
        if frame.size!=(w,h) or depth.shape!=(h,w):raise ValueError('Blender devolvió otra resolución')
        self.medidas.append(dict(indice=self.indice-1,segundos=time.perf_counter()-start,**response))
        (self.raiz/'ejecucion.json').write_text(json.dumps(dict(runtime=self.info,renders=self.medidas),indent=2),encoding='utf8')
        return frame,depth

    def cerrar(self):
        if self.cerrada:return
        self.cerrada=True
        if self.proceso.poll() is None:
            try:self.proceso.stdin.write('{"terminar":true}\n');self.proceso.stdin.flush()
            except (OSError,ValueError):pass
            try:self.proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:self.proceso.kill();self.proceso.wait()
        self.hilo.join(timeout=3)
        for pipe in (self.proceso.stdin,self.proceso.stdout):
            if pipe:
                try:pipe.close()
                except OSError:pass  # Windows: pipe roto no debe ocultar el error bpy
        self.log.close()
        (self.raiz/'cierre.json').write_text(json.dumps(dict(pid=self.proceso.pid,
            retorno=self.proceso.returncode,proceso_terminado=self.proceso.poll() is not None)),encoding='utf8')


def iniciar(paquete,pedido):
    global _sesion
    if _sesion is not None:raise ValueError('Blender ya fue iniciado por el ejecutor')
    _sesion=Sesion(paquete,pedido)


def cerrar():
    if _sesion is not None:_sesion.cerrar()


class Renderer:
    backend='blender'
    def __init__(self,w,h):
        if _sesion is None:raise RuntimeError('Blender debe iniciarlo el ejecutor del Estudio, no el motor')
        self.w,self.h=w,h;self.last_depth=None
        self.ctx=type('ContextoInformativo',(),dict(info={'GL_RENDERER':_sesion.info.get('gpu',{}).get('renderer','Blender')}))()

    def render(self,mesh,cam,sprites=(),ambiente=None,volumen=None):
        frame,self.last_depth=_sesion.render(self.w,self.h,mesh,cam,sprites,ambiente,volumen)
        return frame
