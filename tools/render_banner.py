"""Render the original HSCredit logo with prominent 3D motion and positioning.

python tools/render_banner.py --preview
python tools/render_banner.py
Install tools/requirements-banner.txt first. A desktop OpenGL 3.3 driver is needed.
"""
from pathlib import Path
from io import BytesIO
import argparse
import math
import os
import xml.etree.ElementTree as ET

import cairosvg
import mapbox_earcut
import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from svgpathtools import parse_path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'profile'/'assets'
W,H = 1600,520
SW,SH = 760,600
V = 566.92914
DEPTH = .16
LOOP_MS = 4800


def font(size,bold=False,chinese=False):
    folder=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    name=('msyhbd.ttc' if bold else 'msyh.ttc') if chinese else ('segoeuib.ttf' if bold else 'segoeui.ttf')
    return ImageFont.truetype(str(folder/name),size)


def label(draw,xy,text,size,color,spacing=2):
    f=font(size,True); x,y=xy
    for char in text:
        draw.text((x,y),char,font=f,fill=color)
        x+=draw.textlength(char,font=f)+spacing


def rotation(a,axis):
    c,s=math.cos(a),math.sin(a); m=np.eye(4)
    if axis=='y': m[:3,:3]=[[c,0,s],[0,1,0],[-s,0,c]]
    elif axis=='x': m[:3,:3]=[[1,0,0],[0,c,-s],[0,s,c]]
    else: m[:3,:3]=[[c,-s,0],[s,c,0],[0,0,1]]
    return m


def logo_source():
    root=ET.parse(ASSETS/'hscredit-logo.svg').getroot()
    # Keep exact original paths; omit the duplicate glow group for solid geometry.
    groups=[c for c in root if c.tag.endswith('g') and not c.get('filter')]
    paths=[p.get('d') for group in groups for p in group if p.tag.endswith('path')]
    for child in list(root):
        if child.get('filter'): root.remove(child)
    for parent in root.iter():
        for child in list(parent):
            if child.tag.endswith('animate'): parent.remove(child)
    rgba=Image.open(BytesIO(cairosvg.svg2png(bytestring=ET.tostring(root),output_width=1200,output_height=1200))).convert('RGBA')
    return paths,rgba


def logo_mesh(paths):
    vertices=[]
    def vertex(p,z,n):
        x,y=p
        return [x,y,z,*n,(x*180+V/2)/V,(y*180+V/2)/V]
    for data in paths:
        compound=None
        for subpath in parse_path(data).continuous_subpaths():
            points=[]
            for segment in subpath:
                count=max(2,int(math.ceil(segment.length()/1.5)))
                for t in np.linspace(0,1,count,endpoint=False):
                    q=segment.point(t)
                    points.append(((q.real-V/2)/180,(V/2-q.imag)/180))
            if len(points)<3: continue
            polygon=Polygon(points).buffer(0)
            compound=polygon if compound is None else compound.symmetric_difference(polygon)
        if compound is None: continue
        polygons=list(compound.geoms) if isinstance(compound,MultiPolygon) else [compound]
        for raw in polygons:
            p=orient(raw,sign=1)
            rings=[np.array(p.exterior.coords)[:-1]]+[np.array(r.coords)[:-1] for r in p.interiors]
            coords=np.concatenate(rings)
            ends=np.cumsum([len(r) for r in rings],dtype='uint32')
            indices=mapbox_earcut.triangulate_float64(coords,ends)
            for i in indices: vertices.append(vertex(coords[i],DEPTH,[0,0,1]))
            for i in indices[::-1]: vertices.append(vertex(coords[i],-DEPTH,[0,0,-1]))
            for ring in rings:
                for a,b in zip(ring,np.roll(ring,-1,axis=0)):
                    delta=b-a; normal=np.array([delta[1],-delta[0],0.])
                    normal/=np.linalg.norm(normal)
                    quad=[vertex(a,-DEPTH,normal),vertex(b,-DEPTH,normal),vertex(b,DEPTH,normal),vertex(a,DEPTH,normal)]
                    vertices.extend(quad[i] for i in [0,1,2,0,2,3])
    result=np.array(vertices,dtype='f4')
    assert np.isfinite(result).all()
    return result


def backdrop(logo):
    yy,xx=np.mgrid[:H,:W]
    data=np.zeros((H,W,3))+[6,10,22]
    for x,y,s,c in [(1240,220,300,[24,9,53]),(1050,250,250,[0,12,24]),(450,150,600,[3,5,10])]:
        data+=np.exp(-((xx-x)**2+(yy-y)**2)/(2*s*s))[...,None]*c
    im=Image.fromarray(np.uint8(data),'RGB').convert('RGBA')
    # The watermark is the brand's own silhouette, not an unrelated motif.
    watermark=Image.new('RGBA',(740,740),(112,72,190,0))
    watermark.putalpha(logo.getchannel('A').resize((740,740)).point(lambda x:int(x*.032)))
    im.alpha_composite(watermark,(1030,-125))
    d=ImageDraw.Draw(im)
    d.text((72,45),'衡枢真信',font=font(36,True,True),fill='#dce7f4')
    label(d,(244,60),'HENGSHU CREDIT',21,'#98b2cc',1.8)
    # Copy is extracted from the website and project READMEs; see root README.
    d.text((69,116),'专注金融风控',font=font(70,True,True),fill='#f5f8ff')
    d.text((69,199),'技术与服务',font=font(70,True,True),fill='#b9b3ff')
    d.text((74,298),'风控能力输出 · 模型评分服务 · 分析工具开源',font=font(27,chinese=True),fill='#b9cbe0')
    d.line((75,347,827,347),fill='#32445f',width=1)
    products=[('HSCredit','全流程量化工具箱',75),('天枢决策引擎','可视化风控决策平台',333),
              ('瑶光营销平台','用户营销与客户触达',591)]
    for product,capability,x in products:
        d.text((x,366),product,font=font(29,True,product!='HSCredit'),fill='#e0eaf7')
        d.text((x,410),capability,font=font(24,chinese=True),fill='#a9bfd7')
    label(d,(75,478),'HENGSHUCREDIT.COM',17,'#88a5c2',1.8)
    return im


VERTEX='''#version 330
in vec3 in_pos; in vec3 in_normal; in vec2 in_uv;
uniform mat4 model; uniform mat4 vp;
out vec3 pos; out vec3 n; out vec2 uv; out float face;
void main(){vec4 p=model*vec4(in_pos,1.);pos=p.xyz;n=mat3(model)*in_normal;
uv=in_uv;face=abs(in_normal.z);gl_Position=vp*p;}
'''
FRAGMENT='''#version 330
in vec3 pos;in vec3 n;in vec2 uv;in float face;
uniform sampler2D logo;uniform sampler2D bevel;uniform mat4 model;uniform float phase;out vec4 color;
void main(){
 vec3 bevelNormal=mat3(model)*(texture(bevel,uv).rgb*2.-1.);
 vec3 norm=normalize(mix(n,bevelNormal,step(.5,face))),view=normalize(vec3(0.,0.,7.2)-pos);
 vec3 light=normalize(vec3(-3.+sin(phase)*4.,4.,6.)-pos);
 float diffuse=max(dot(norm,light),0.);
 float spec=pow(max(dot(norm,normalize(light+view)),0.),80.);
 vec3 original=texture(logo,uv).rgb;
 float sweep=exp(-pow((uv.x+.3*uv.y-(.65+.8*sin(phase)))*10.,2.));
 vec3 front=original*(.88+.12*diffuse)+vec3(.18,.24,.3)*spec+vec3(.22,.32,.40)*sweep;
 float hue=clamp(uv.x*.6+(1.-uv.y)*.4,0.,1.);
 vec3 edge=mix(vec3(.06,.40,.62),vec3(.31,.07,.52),hue);
 vec3 side=edge*(.5+.7*diffuse)+vec3(.3,.4,.6)*spec;
 color=vec4(mix(side,front,step(.5,face)),1.);
}
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');parser.add_argument('--frames',type=int,default=96)
    args=parser.parse_args();paths,logo=logo_source();geometry=logo_mesh(paths)
    ctx=moderngl.create_standalone_context(require=330)
    print('Rendering original logo:',len(geometry)//3,'triangles;',ctx.info['GL_RENDERER'],flush=True)
    prog=ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
    tex=ctx.texture(logo.size,4,logo.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes());tex.use(0)
    tex.filter=(moderngl.LINEAR,moderngl.LINEAR)
    prog['logo'].value=0
    # A small rounded bevel adds edge highlights without changing the outline.
    distance=distance_transform_edt(np.asarray(logo.getchannel('A'))>128)
    height=.025*np.sqrt(1-np.clip(1-distance/9,0,1)**2)
    gy,gx=np.gradient(height,(V/180)/1200)
    normals=np.stack([-gx,gy,np.ones_like(gx)],axis=-1)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    normal_image=Image.fromarray(np.uint8(np.clip(normals*.5+.5,0,1)*255),'RGB')
    bevel=ctx.texture(logo.size,3,normal_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes())
    bevel.filter=(moderngl.LINEAR,moderngl.LINEAR);bevel.use(1);prog['bevel'].value=1
    vao=ctx.vertex_array(prog,[(ctx.buffer(geometry),'3f 3f 2f','in_pos','in_normal','in_uv')])
    f=1/math.tan(math.radians(36)/2)
    projection=np.array([[f/(SW/SH),0,0,0],[0,f,0,0],[0,0,-1.004,-.2004],[0,0,-1,0]])
    view=np.eye(4);view[2,3]=-7.2
    prog['vp'].write((projection@view).T.astype('f4').tobytes())
    samples=min(4,ctx.max_samples)
    ms=ctx.framebuffer(ctx.renderbuffer((SW,SH),components=4,samples=samples),ctx.depth_renderbuffer((SW,SH),samples=samples))
    fbo=ctx.simple_framebuffer((SW,SH),components=4);ctx.enable(moderngl.DEPTH_TEST)
    bg=backdrop(logo);frames=[];count=1 if args.preview else args.frames
    for i in range(count):
        phase=math.tau*i/args.frames
        model=rotation(.08+.62*math.sin(phase),'y')@rotation(.16*math.cos(phase),'x')@rotation(.035*math.sin(phase),'z')
        model[:3,:3]*=1.+.035*math.sin(phase)
        model[1,3]=.09*math.sin(2*phase)
        prog['model'].write(model.T.astype('f4').tobytes());prog['phase'].value=phase
        ms.use();ms.clear(0,0,0,0);vao.render();ctx.copy_framebuffer(fbo,ms)
        scene=Image.frombytes('RGBA',(SW,SH),fbo.read(components=4,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        frame=bg.copy()
        glow=scene.filter(ImageFilter.GaussianBlur(20))
        intensity=.26+.10*math.sin(phase)
        glow.putalpha(glow.getchannel('A').point(lambda a:int(a*intensity)))
        frame.alpha_composite(glow,(790,-40));frame.alpha_composite(scene,(790,-40))
        mask=Image.new('L',(W,H));ImageDraw.Draw(mask).rounded_rectangle((0,0,W-1,H-1),radius=24,fill=255)
        frame.putalpha(mask)
        if i==0: frame.save(ASSETS/'banner-static.png',optimize=True)
        frames.append(frame.convert('RGB').resize((1440,468),Image.Resampling.LANCZOS))
        if i%24==0: print(f'Rendered {i+1}/{count}',flush=True)
    if not args.preview:
        # Give the logo extra palette weight so gradients retain their brand colors.
        samples=[]
        for i in range(0,count,8):
            samples.append(frames[i].resize((320,104)))
            samples.append(frames[i].crop((870,20,1230,425)).resize((320,360)))
        atlas=Image.new('RGB',(320,sum(im.height for im in samples)))
        y=0
        for im in samples:
            atlas.paste(im,(0,y));y+=im.height
        palette=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
        indexed=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
        durations=[round((i+1)*(LOOP_MS/10)/args.frames)*10-round(i*(LOOP_MS/10)/args.frames)*10 for i in range(args.frames)]
        frames[0].save(ASSETS/'banner.webp',format='WEBP',save_all=True,append_images=frames[1:],duration=durations,loop=0,lossless=True,method=4)
        indexed[0].save(ASSETS/'banner.gif',save_all=True,append_images=indexed[1:],duration=durations,loop=0,optimize=True,disposal=1)
        print('Lossless WebP bytes:',(ASSETS/'banner.webp').stat().st_size,flush=True)
        print('GIF bytes:',(ASSETS/'banner.gif').stat().st_size,flush=True)


if __name__=='__main__':main()
