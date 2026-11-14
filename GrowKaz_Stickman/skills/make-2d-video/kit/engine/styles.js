// engine/styles.js — colour moods + switchable visual styles.
// A MOOD is the lighting situation of a location (day, dusk, night, storm, interiors, void).
// A STYLE re-grades every mood (palette overrides + a lift/gamma/gain colour grade on the final frame + post settings).
// grade: contrast (around mid-grey), sat (saturation), lift/gamma/gain per RGB channel (lift tints shadows, gain tints highlights).
// Scenes must take colours from mood()/S() so a style switch re-themes the whole video.

export const BASE_MOODS = {
  day:          { sky: ['#8fb0d8', '#cfdcea', '#efe3d2'], ambient: '#6f7d96', key: '#fff3dc', rim: '#fff1d6', wall: '#8d8496', floor: '#5f5866', dark: '#2f2a36', practical: '#ffe2a8', grass: '#4f8a55', road: '#5d5a66', fog: '#dfe4f0' },
  golden:       { sky: ['#6b5a8e', '#e89a6a', '#f9d49c'], ambient: '#4a3a50', key: '#ffcf8f', rim: '#ffc68a', wall: '#5a3a34', floor: '#45302a', dark: '#2a1814', practical: '#ffe7b0', grass: '#4d6b3c', road: '#4a3c40', fog: '#f0c49a' },
  dusk:         { sky: ['#3d3360', '#8a5a86', '#e8956b', '#f7cf98'], ambient: '#3b2b3d', key: '#ffc68a', rim: '#ffc68a', wall: '#4a3646', floor: '#3d2c38', dark: '#231a27', practical: '#ffd59a', grass: '#3d5a48', road: '#3a3040', fog: '#c08a8a' },
  night:        { sky: ['#0b1028', '#1d2550', '#3a3570'], ambient: '#1e2444', key: '#c9d4ff', rim: '#a9b8ff', wall: '#262a46', floor: '#1b1e33', dark: '#0f1122', practical: '#ffb860', grass: '#22433a', road: '#24263a', fog: '#3a4270' },
  storm:        { sky: ['#141a33', '#2a3358', '#3d4670'], ambient: '#232a48', key: '#dfe6ff', rim: '#cfd9ff', wall: '#2b3150', floor: '#1c2238', dark: '#0d1020', practical: '#bcd0ff', grass: '#25483e', road: '#232838', fog: '#4a5580' },
  interiorWarm: { sky: ['#c98a74', '#f2b585', '#f7cf98'], ambient: '#4a3646', key: '#ffd59a', rim: '#ffcf8f', wall: '#4f3a40', floor: '#3a2a2e', dark: '#21171c', practical: '#ffd28a', grass: '#3d5a48', road: '#3a3040', fog: '#a87a70' },
  interiorCool: { sky: ['#2a3560', '#5a6aa0'], ambient: '#2a2c48', key: '#cbd6ff', rim: '#b8c6ff', wall: '#2e3150', floor: '#22243a', dark: '#121426', practical: '#9fe0ff', grass: '#22433a', road: '#24263a', fog: '#4a5080' },
  void:         { sky: ['#0a0e1a', '#121a2e'], ambient: '#151c30', key: '#ffffff', rim: '#8fb8e8', wall: '#121a2e', floor: '#0d1322', dark: '#070a12', practical: '#ffd47e', grass: '#1d3a33', road: '#151a28', fog: '#1d2740' },
};

const UI = { card: 'rgba(18,28,48,.94)', cardLine: 'rgba(150,180,230,.25)', text: '#9fb6d8', sub: '#6f84a6', accent: '#ff6f61', gold: '#ffd47e', cream: '#fff1dc', blueprint: '#8fb8e8', bpBg: '#0b1324', good: '#5fd39a' };

export const STYLES = {
  emerald: {
    name: 'GrowKaz Emerald', desc: 'GrowKaz signature look: deep forest-green shadows, warm gold key light, electric lime rim light, rich bloom.',
    ink: '#06110c', inkFar: '#1c3328', feature: '#f2ffe8', rimWidth: 4.5,
    ui: { ...UI, card: 'rgba(8,30,22,.94)', cardLine: 'rgba(140,255,170,.28)', text: '#a8e8c0', sub: '#6fa88a', accent: '#c6ff3d', gold: '#ffd45a', blueprint: '#7dffb0', bpBg: '#061a12', good: '#c6ff3d' },
    grade: { contrast: 1.08, sat: 1.15, lift: [0.0, 0.035, 0.02], gamma: [0.96, 1.06, 0.96], gain: [1.02, 1.1, 0.88], vignette: 0.6, grain: 0.05, bloom: 0.8 },
    moods: {
      dusk: { sky: ['#0c2a22', '#1f5a44', '#7ab05a', '#f2d36a'], key: '#ffd77a', rim: '#c6ff3d', wall: '#1e3a30', floor: '#152a22', dark: '#0a1812', practical: '#ffe28a', fog: '#5a8a6a' },
      golden: { sky: ['#1a4a38', '#8ab04a', '#f6d45a'], rim: '#d8ff6a', key: '#ffd36a' },
      night: { sky: ['#03100c', '#0a2a20', '#164a36'], rim: '#7dffb0', practical: '#ffd45a', wall: '#10261e' },
      interiorWarm: { rim: '#c6ff3d', wall: '#233a2e', practical: '#ffd45a' },
      void: { sky: ['#03100c', '#08201a'], rim: '#7dffb0' },
    },
  },
  ember: {
    name: 'Ember Forge', desc: 'Charcoal-black world lit by fire: crimson shadows, molten copper rim light, hot orange glows, heavy contrast.',
    ink: '#0c0606', inkFar: '#2e1614', feature: '#fff0e0', rimWidth: 4,
    ui: { ...UI, card: 'rgba(30,12,10,.94)', cardLine: 'rgba(255,140,90,.3)', text: '#f0b49a', sub: '#a8705c', accent: '#ff3d2e', gold: '#ffa53d', blueprint: '#ff9a6a', bpBg: '#1a0806', good: '#ffc53d' },
    grade: { contrast: 1.18, sat: 1.2, lift: [0.05, 0.0, 0.0], gamma: [1.08, 0.94, 0.86], gain: [1.2, 0.95, 0.75], vignette: 0.75, grain: 0.065, bloom: 0.85 },
    moods: {
      dusk: { sky: ['#1a0606', '#5a140e', '#c8401e', '#ffa040'], key: '#ff9a4a', rim: '#ff7a2e', wall: '#3a1612', floor: '#2a100c', dark: '#140606', practical: '#ffb050', fog: '#8a3a26' },
      night: { sky: ['#0a0404', '#2a0a08', '#5a1a10'], rim: '#ff6a2e', practical: '#ffa53d', wall: '#241010' },
      golden: { sky: ['#4a1a10', '#d0602a', '#ffb860'], rim: '#ff8a3a' },
      interiorWarm: { rim: '#ff7a2e', wall: '#3a1a16' },
    },
  },
  arctic: {
    name: 'Arctic Glass', desc: 'Clean icy world: pale steel-teal shadows, crisp white key, bright cyan rim light, cool and sharp, almost no grain.',
    ink: '#08121a', inkFar: '#2a4050', feature: '#f4fdff', rimWidth: 4,
    ui: { ...UI, card: 'rgba(10,30,44,.92)', cardLine: 'rgba(160,240,255,.3)', text: '#bfefff', sub: '#7aaabf', accent: '#3de0ff', gold: '#e8fbff', blueprint: '#9af2ff', bpBg: '#071822', good: '#5fffd2' },
    grade: { contrast: 1.04, sat: 0.82, lift: [0.02, 0.05, 0.07], gamma: [0.94, 1.02, 1.08], gain: [0.92, 1.04, 1.12], vignette: 0.4, grain: 0.025, bloom: 0.65 },
    moods: {
      dusk: { sky: ['#123044', '#2e6a86', '#8ad0e0', '#e6f8ff'], key: '#eaf8ff', rim: '#7ff0ff', wall: '#2a4656', floor: '#1e3442', dark: '#0e1e28', practical: '#c8f6ff', fog: '#8ab8c8' },
      golden: { sky: ['#2a5a76', '#a0d8e8', '#f0fcff'], rim: '#a8f6ff', key: '#f4fcff' },
      night: { sky: ['#040e16', '#0c2636', '#18465a'], rim: '#5fe8ff', practical: '#e8fbff' },
      interiorWarm: { rim: '#9af2ff', wall: '#2e4a58', practical: '#e0faff' },
    },
  },
  sakura: {
    name: 'Sakura Bloom', desc: 'Dreamy rose-and-peach world: plum shadows, soft pink sky, warm peach key, glowing rose rim light, gentle haze.',
    ink: '#1a0c16', inkFar: '#4a2a40', feature: '#fff4f6', rimWidth: 5,
    ui: { ...UI, card: 'rgba(50,20,40,.9)', cardLine: 'rgba(255,170,210,.3)', text: '#ffc4dc', sub: '#c088a4', accent: '#ff5fa0', gold: '#ffd0a0', blueprint: '#ffb0d4', bpBg: '#220e1c', good: '#ffa0c8' },
    grade: { contrast: 0.95, sat: 1.05, lift: [0.07, 0.03, 0.06], gamma: [1.08, 1.0, 1.04], gain: [1.1, 0.96, 1.02], vignette: 0.35, grain: 0.05, bloom: 0.7 },
    moods: {
      dusk: { sky: ['#4a2050', '#b05a8a', '#f2a0b4', '#ffe0d0'], key: '#ffcfb0', rim: '#ffa0c8', wall: '#5a3048', floor: '#46243a', dark: '#2a1222', practical: '#ffd8c0', fog: '#d08aa8' },
      night: { sky: ['#1a0a24', '#3a1a48', '#6a3a70'], rim: '#ff9ad0', practical: '#ffc8a0' },
      golden: { sky: ['#8a4a7a', '#f2a0a0', '#ffe4c4'], rim: '#ffb4c8' },
      interiorWarm: { rim: '#ffa0c8', wall: '#5a3448' },
    },
  },
  retro: {
    name: 'Retro Print', desc: 'Vintage poster look: faded teal and mustard, sepia-warm highlights, low saturation, flat contrast, heavy print grain.',
    ink: '#1c1612', inkFar: '#4a4036', feature: '#fbf2dc', rimWidth: 5.5,
    ui: { ...UI, card: 'rgba(36,40,36,.92)', cardLine: 'rgba(230,200,140,.3)', text: '#e8d8b0', sub: '#a89878', accent: '#e8603a', gold: '#e8b83a', blueprint: '#8ac0b0', bpBg: '#1a2420', good: '#9ac06a' },
    grade: { contrast: 0.9, sat: 0.7, lift: [0.08, 0.07, 0.05], gamma: [1.06, 1.04, 0.96], gain: [1.06, 1.0, 0.86], vignette: 0.5, grain: 0.11, bloom: 0.35 },
    moods: {
      dusk: { sky: ['#2a4a48', '#5a8a80', '#e0a050', '#f2d8a0'], key: '#f2c880', rim: '#f2c070', wall: '#4a4038', floor: '#3a322c', dark: '#221c18', practical: '#f2d090', fog: '#a89070' },
      night: { sky: ['#14201e', '#24403c', '#3a5a54'], rim: '#e8c070', practical: '#e8603a' },
      golden: { sky: ['#4a7a70', '#e0a050', '#f6dca8'], rim: '#f6c87a' },
    },
  },
};
export const STYLE_IDS = Object.keys(STYLES);
