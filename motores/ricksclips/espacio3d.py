"""Renderer local OpenGL 3.3. Metros, Y arriba; no imágenes de referencia.

Triángulos con normales/materiales, perspectiva, z-buffer, shadow map PCF,
billboards RGBA con descarte alfa que reciben/proyectan sombras y volumen
procedural integrado contra la profundidad. PIL es únicamente el contrato final.
"""
import math
import numpy as np
import moderngl
from PIL import Image, ImageFilter


def normal(v):
    v = np.asarray(v, dtype='f4')
    return v / max(float(np.linalg.norm(v)), 1e-8)


def mirar(eye, target):
    f = normal(np.array(target) - eye)
    r = normal(np.cross(f, (0, 1, 0)))
    u = np.cross(r, f)
    m = np.eye(4, dtype='f4')
    m[:3, :3] = np.array([r, u, -f])
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspectiva(fov, aspect, near=.1, far=180):
    f = 1 / math.tan(math.radians(fov) / 2)
    return np.array([[f/aspect,0,0,0], [0,f,0,0],
        [0,0,(far+near)/(near-far),2*far*near/(near-far)], [0,0,-1,0]], dtype='f4')


def ortho(r=32, far=120):
    return np.array([[1/r,0,0,0], [0,1/r,0,0], [0,0,-2/far,-1], [0,0,0,1]], dtype='f4')


VERT = '''#version 330
in vec3 pos; in vec3 nor; in vec3 tint; in float glow;
uniform mat4 vp; uniform mat4 lightvp;
out vec3 world; out vec3 n; out vec3 color; out float emission; out vec4 ls;
void main(){world=pos;n=nor;color=tint;emission=glow;ls=lightvp*vec4(pos,1);gl_Position=vp*vec4(pos,1);}
'''
LIGHT = '''
uniform sampler2D shadowmap; uniform vec3 lightdir; uniform vec3 eye;
uniform vec3 fogcolor; uniform vec3 lamp; uniform float lampgain; uniform float fog;
float visibility(vec4 ls,vec3 n){
 vec3 p=ls.xyz/ls.w*.5+.5;
 if(p.x<0||p.x>1||p.y<0||p.y>1||p.z>1)return 1;
 float a=0;float bias=max(.002,.004*(1-dot(n,lightdir)));
 for(int x=-1;x<=1;x++)for(int y=-1;y<=1;y++)
 a+=p.z-bias<=texture(shadowmap,p.xy+vec2(x,y)/1536.).r?1.:.28;
 return a/9.;
}
vec3 lighting(vec3 c,vec3 n,vec3 w,vec4 ls,float em){
 float diffuse=max(0,dot(normalize(n),lightdir));
 float cel=mix(diffuse,smoothstep(.08,.88,diffuse),.35);
  vec3 nn=normalize(n);
  vec3 ambient=mix(vec3(.24,.19,.20),vec3(.32,.44,.64),nn.y*.5+.5);
  float vis=visibility(ls,nn);
  // Ciel froid dans les ombres, rebond ocre sur les faces basses, clé chaude.
  vec3 bounce=vec3(.17,.085,.035)*max(0.,-nn.y);
  vec3 lit=c*(ambient+bounce+vec3(1.10,.86,.61)*cel*vis);
 float d=length(lamp-w);
 lit+=c*vec3(1.,.48,.16)*lampgain/(1.+d*d*.22)*max(.12,dot(normalize(n),normalize(lamp-w)));
 lit=mix(lit,c*1.6,em);
 return mix(lit,fogcolor,1.-exp(-length(eye-w)*fog));
}
'''
FRAG = '#version 330\n' + LIGHT + '''
in vec3 world; in vec3 n; in vec3 color; in float emission; in vec4 ls;
out vec4 outcolor;
float hash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
 mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
void main(){
 // Materiales en coordenadas de objeto/mundo: no ruido uniforme sobre todo.
 float mat=max(0.,-emission);vec3 c=color;vec3 nn=normalize(n);
 float broad=noise(world*1.4);
 if(mat>.5&&mat<1.5){ // madera: fibra longitudinal y vetas, no manchas pétreas
   vec3 q=abs(nn.y)>.5?world.zxy:world.xyz;
   float grain=sin(q.y*72.+noise(q*vec3(.7,9.,2.))*5.);
   c*=.90+.09*grain+.12*noise(q*vec3(.3,13.,3.));
 }else if(mat>1.5&&mat<2.5){ // arenisca estratificada
    float strata=sin(world.y*1.9+noise(world*vec3(.15,.25,.15))*.65);
    c*=.94+.09*broad+.035*strata;
    c=mix(c,c*vec3(.78,.57,.45),smoothstep(.95,.999,sin(world.y*2.7+noise(world*.2)))*.16);
 }else if(mat>2.5&&mat<3.5){ // acero: lóbulo spéculaire étroit, couleur intacte
   vec3 halfv=normalize(lightdir+normalize(eye-world));
   c*=.92+.08*noise(world*vec3(35.,3.,2.));
   c+=vec3(.65,.72,.81)*pow(max(0.,dot(nn,halfv)),65.)*.65;
 }else if(mat>3.5&&mat<4.5){ // agua: Fresnel, reflejo del cielo y espuma en crestas
   nn=normalize(nn+vec3(sin(world.z*8.+sin(world.x*4.))*.08,0.,cos(world.x*9.+world.z*3.)*.08));
   float fres=pow(1.-max(0.,dot(nn,normalize(eye-world))),3.);
   c=mix(c,vec3(.29,.55,.94),fres*.65);
   vec3 hv=normalize(lightdir+normalize(eye-world));
   c+=vec3(.60,.78,1.)*pow(max(0.,dot(nn,hv)),95.)*.65;
   float foam=smoothstep(4.7,5.5,world.y+noise(world*5.)*.3);
   c=mix(c,vec3(.77,.91,1.),foam);
 }else if(mat>4.5&&mat<5.5){
   c*=.90+.18*broad+.05*noise(world*14.);
 }else{c*=.96+.06*broad;}
 outcolor=vec4(lighting(c,nn,world,ls,max(0.,emission)),1);
}
'''
SVERT = '''#version 330
in vec3 pos; in vec2 uv; uniform mat4 vp; uniform mat4 lightvp;
out vec2 texcoord; out vec3 world; out vec4 ls;
void main(){texcoord=uv;world=pos;ls=lightvp*vec4(pos,1);gl_Position=vp*vec4(pos,1);}
'''
SFRAG = '#version 330\n' + LIGHT + '''
uniform sampler2D sprite; uniform vec3 facing; uniform bool shadowpass;
in vec2 texcoord; in vec3 world; in vec4 ls; out vec4 outcolor;
void main(){vec4 c=texture(sprite,texcoord);if(c.a<.3)discard;
 if(shadowpass){outcolor=vec4(1);return;}
 // El dibujo 2D conserva sus tintas; solo integración suave en la luz del lugar.
 vec3 lit=lighting(c.rgb, facing,world,ls,0.);
 outcolor=vec4(mix(c.rgb,lit,.38),c.a);}
'''
FULL = '''#version 330
in vec2 pos;out vec2 uv;
void main(){uv=pos*.5+.5;gl_Position=vec4(pos,0,1);}
'''
VOLUME = '''#version 330
uniform sampler2D frame;uniform sampler2D depthtex;uniform mat4 invvp;
uniform vec3 eye;uniform float time;uniform float amount;uniform vec3 center;
in vec2 uv;out vec4 outcolor;
float hash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
 mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){return noise(p)*.57+noise(p*2.03)*.28+noise(p*4.1)*.15;}
float density(vec3 p){
  vec3 q=p-center;float h=clamp(time,0.,4.);
  q+=vec3(fbm(q*1.2+time*.18),fbm(q*.9-time*.22),fbm(q*1.1+time*.1))*.9-.45;
 float stem=length(q.xz)/(1.+h*.22);
 float a=max(0.,1.-stem)*smoothstep(0.,.6,q.y)*(1.-smoothstep(3.+h,6.+h,q.y));
 vec3 cap=q-vec3(0,3.+h,0);cap.y*=1.8;
 float b=max(0.,1.-length(cap)/(1.3+h*.95));
  return max(0.,a+b-.12)*(.25+.95*fbm(p*1.4-vec3(0,time*.7,0)))*amount;
}
void main(){
 vec4 c=texture(frame,uv);float d=texture(depthtex,uv).r;
 vec4 endp=invvp*vec4(uv*2.-1.,d*2.-1.,1);vec3 end=endp.xyz/endp.w;
 vec3 ray=normalize(end-eye);float maxdist=min(length(end-eye),80.);
 vec3 acc=vec3(0);float alpha=0.;
 for(int i=0;i<128;i++){
 float dist=(float(i)+.5)*maxdist/128.;vec3 p=eye+ray*dist;float rho=density(p);
 float a=1.-exp(-rho*maxdist/128.*1.5);
 float lit=clamp(1.-density(p+vec3(-.6,1.,.3))*.5,.25,1.);
 float fire=exp(-max(time-.6,0.)*1.4)*max(0.,1.-length(p-center-vec3(0,2,0))/5.);
 vec3 col=mix(vec3(.25,.17,.23)*lit+vec3(.23,.13,.08),vec3(2.,.55,.035),fire);
 acc+=(1.-alpha)*a*col;alpha+=(1.-alpha)*a;if(alpha>.98)break;
 }
 outcolor=vec4(c.rgb*(1.-alpha)+acc,1);
}
'''


class Malla:
    def __init__(self):
        self.vertices = []
        self.material = 0

    def triangulo(self, a, b, c, color, em=0):
        n = normal(np.cross(np.subtract(b,a), np.subtract(c,a)))
        col = tuple(int(color[i:i+2],16)/255 for i in (1,3,5)) if isinstance(color,str) else color
        for p in (a,b,c):
            self.vertices.append((*p,*n,*col,em if em else -self.material))

    def torno(self,p,perfil,color,lados=32,em=0):
        """Perfil (radio,altura) girado en Y: cascos, vasos, aros y cuencos huecos."""
        x,y,z=p
        for (r0,h0),(r1,h1) in zip(perfil,perfil[1:]):
            for j in range(lados):
                a=j*math.tau/lados;b=(j+1)*math.tau/lados
                self.quad((x+r0*math.cos(a),y+h0,z+r0*math.sin(a)),
                    (x+r1*math.cos(a),y+h1,z+r1*math.sin(a)),
                    (x+r1*math.cos(b),y+h1,z+r1*math.sin(b)),
                    (x+r0*math.cos(b),y+h0,z+r0*math.sin(b)),color,em)

    def quad(self, a,b,c,d,color,em=0):
        self.triangulo(a,b,c,color,em); self.triangulo(a,c,d,color,em)

    def caja(self, p, size, color, em=0):
        x,y,z=p; w,h,d=np.array(size)/2
        v=[(x+sx*w,y+sy*h,z+sz*d) for sx,sy,sz in
           ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
        for ids in ((0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)):
            self.quad(*(v[i] for i in ids),color,em)

    def caja_girada(self,p,size,color,giro=0):
        """Caja rígida con rotación Y en radianes, conserva normales y material."""
        local=Malla();local.material=self.material;local.caja((0,0,0),size,color)
        c,s=math.cos(giro),math.sin(giro)
        for x,y,z,nx,ny,nz,*rest in local.vertices:
            self.vertices.append((p[0]+c*x+s*z,p[1]+y,p[2]-s*x+c*z,c*nx+s*nz,ny,-s*nx+c*nz,*rest))

    def barra(self, a,b,r,color, lados=6):
        a,b=np.array(a),np.array(b); axis=normal(b-a)
        ref=(0,1,0) if abs(axis[1])<.95 else (1,0,0)
        u=normal(np.cross(axis,ref))*r;v=np.cross(axis,u)
        for i in range(lados):
            q=u*math.cos(i*math.tau/lados)+v*math.sin(i*math.tau/lados)
            s=u*math.cos((i+1)*math.tau/lados)+v*math.sin((i+1)*math.tau/lados)
            self.quad(a+s,b+s,b+q,a+q,color)
            self.triangulo(a,a+s,a+q,color); self.triangulo(b,b+q,b+s,color)

    def esfera(self,p,r,color, rings=8, lados=16,em=0):
        p=np.array(p);r=np.array(r if isinstance(r,(tuple,list,np.ndarray)) else (r,r,r))
        def v(i,j):
            lat=-math.pi/2+math.pi*i/rings;lon=math.tau*j/lados
            return p+r*np.array((math.cos(lat)*math.cos(lon),math.sin(lat),math.cos(lat)*math.sin(lon)))
        for i in range(rings):
            for j in range(lados):
                start=len(self.vertices)
                self.quad(v(i+1,j),v(i+1,j+1),v(i,j+1),v(i,j),color,em)
                # Normale analytique d'ellipsoïde: volume inchangé, pas de flou.
                for k in range(start,len(self.vertices)):
                    vv=self.vertices[k];nn=normal((np.array(vv[:3])-p)/np.maximum(r*r,1e-12))
                    self.vertices[k]=(*vv[:3],*nn,*vv[6:])


class Renderer:
    def __init__(self,w,h):
        self.w,self.h=w,h
        self.ctx=moderngl.create_standalone_context(require=330)
        c=self.ctx
        self.program=c.program(vertex_shader=VERT,fragment_shader=FRAG)
        self.shadowprog=c.program(vertex_shader='''#version 330
in vec3 pos;uniform mat4 vp;void main(){gl_Position=vp*vec4(pos,1);}''',fragment_shader='''#version 330
out vec4 c;void main(){c=vec4(1);}''')
        self.spriteprog=c.program(vertex_shader=SVERT,fragment_shader=SFRAG)
        self.volumeprog=c.program(vertex_shader=FULL,fragment_shader=VOLUME)
        self.color=c.texture((w,h),4);self.depth=c.depth_texture((w,h));self.depth.compare_func=''
        self.fbo=c.framebuffer([self.color],self.depth)
        self.outtex=c.texture((w,h),4);self.out=c.framebuffer([self.outtex])
        self.sh=c.depth_texture((1536,1536));self.sh.compare_func='';self.sh.repeat_x=False;self.sh.repeat_y=False
        self.shf=c.framebuffer(depth_attachment=self.sh)
        self.fullbuf=c.buffer(np.array([[-1,-1],[1,-1],[-1,1],[1,1]],dtype='f4').tobytes())
        self.fullvao=c.vertex_array(self.volumeprog,[(self.fullbuf,'2f','pos')])
        self.last_depth=None

    def _mat(self,p,name,m):
        p[name].write(np.asarray(m,dtype='f4').T.tobytes())

    def render(self,mesh,cam,sprites=(),ambiente=None,volumen=None):
        c=self.ctx;a=ambiente or {}; eye=np.array(cam['eye'],dtype='f4');target=np.array(cam['target'],dtype='f4')
        vp=perspectiva(cam.get('fov',48),self.w/self.h) @ mirar(eye,target)
        light=normal(a.get('sol',(-.6,1,.5)))
        focus=np.array(a.get('centro_sombra',(0,0,-5)))
        lightvp=ortho() @ mirar(focus+light*55,focus)
        data=np.asarray(mesh.vertices,dtype='f4');buf=c.buffer(data.tobytes())
        vao=c.vertex_array(self.program,[(buf,'3f 3f 3f 1f','pos','nor','tint','glow')])
        shvao=c.vertex_array(self.shadowprog,[(buf,'3f 28x','pos')])
        spriteitems=[]
        # Billboard vertical en mundo, orientado al observador: su alfa participa
        # en ambos pases, no es una pegatina posterior sin oclusión.
        right=normal(np.cross(normal(target-eye),(0,1,0)))
        facing=normal((eye[0]-target[0],0,eye[2]-target[2]))
        for image,pos,height in sprites:
            tex=c.texture(image.size,4,image.tobytes());tex.filter=(moderngl.LINEAR,moderngl.LINEAR)
            p=np.array(pos); ww=height*image.width/image.height
            bl=p-right*ww/2; br=p+right*ww/2;tl=bl+(0,height,0);tr=br+(0,height,0)
            vertices=np.array([(*bl,0,1),(*br,1,1),(*tl,0,0),(*tr,1,0)],dtype='f4')
            sb=c.buffer(vertices.tobytes());sv=c.vertex_array(self.spriteprog,[(sb,'3f 2f','pos','uv')])
            spriteitems.append((tex,sb,sv))
        c.enable(moderngl.DEPTH_TEST);c.disable(moderngl.BLEND)
        self.shf.use();self.shf.clear(depth=1);c.viewport=(0,0,1536,1536)
        self._mat(self.shadowprog,'vp',lightvp);shvao.render()
        sp=self.spriteprog
        self._mat(sp,'lightvp',lightvp);self._mat(sp,'vp',lightvp)
        sp['shadowpass'].value=True;sp['sprite'].value=1
        # No leer el shadow map mientras es el destino.
        self.depth.use(0)
        for tex,sb,sv in spriteitems:tex.use(1);sv.render(moderngl.TRIANGLE_STRIP)
        self.fbo.use();c.viewport=(0,0,self.w,self.h)
        sky=a.get('cielo',(.12,.40,.78));self.fbo.clear(*sky,1,depth=1)
        self.sh.use(0)
        for prog in (self.program,sp):
            self._mat(prog,'vp',vp);self._mat(prog,'lightvp',lightvp)
            for name,val in dict(shadowmap=0,lightdir=tuple(light),eye=tuple(eye),fogcolor=sky,
                    lamp=tuple(a.get('lampara',(0,5,0))),lampgain=a.get('potencia',0.),fog=a.get('niebla',.007)).items():
                prog[name].value=val
        vao.render()
        sp['shadowpass'].value=False;sp['facing'].value=tuple(facing)
        for tex,sb,sv in spriteitems:tex.use(1);sv.render(moderngl.TRIANGLE_STRIP)
        source=self.fbo
        if volumen:
            self.out.use();c.disable(moderngl.DEPTH_TEST)
            self.color.use(0);self.depth.use(1);p=self.volumeprog
            p['frame'].value=0;p['depthtex'].value=1;p['eye'].value=tuple(eye)
            self._mat(p,'invvp',np.linalg.inv(vp))
            p['time'].value=volumen['t'];p['amount'].value=volumen.get('cantidad',1.)
            p['center'].value=tuple(volumen.get('pos',(0,0,-6)))
            self.fullvao.render(moderngl.TRIANGLE_STRIP);source=self.out
        im=Image.frombytes('RGB',(self.w,self.h),source.read(components=3)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        depth=np.frombuffer(self.depth.read(),dtype='f4').reshape(self.h,self.w)[::-1].copy()
        self.last_depth=depth
        # Profundidad de campo guiada por profundidad lineal, no blur de todo el fondo.
        z=18/(180-depth*179.9)
        dist=float(np.linalg.norm(target-eye)); aperture=cam.get('apertura',.25)
        coc=np.clip(np.abs(z-dist)/np.maximum(z,1)*aperture,0,1)
        if aperture:
            im=Image.composite(im.filter(ImageFilter.GaussianBlur(self.h/220)),im,Image.fromarray((coc*160).astype('uint8')))
        for tex,sb,sv in spriteitems:sv.release();sb.release();tex.release()
        vao.release();shvao.release();buf.release()
        return im
