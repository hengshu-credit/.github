"""Assemble the original HSCredit logo, then give it one eased 360-degree turn.

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
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from svgpathtools import parse_path, Path as SVGPath, CubicBezier

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'profile'/'assets'
W,H = 1600,520
SW,SH = 760,600
V = 566.92914
DEPTH = .10
LOOP_MS = 9200
POSTER_MS = 2520


def smoothstep(value):
    t=float(np.clip(value,0,1))
    return t*t*t*(10+t*(-15+6*t))


def animation_state(seconds):
    """Assembly, readable hold, slow-fast-slow full turn, hold, fade and reset."""
    turn=smoothstep((seconds-2.8)/4.4)*math.tau
    fade=1.-smoothstep((seconds-8.4)/.5)
    return turn,fade


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


def stroke_reveal_field(path,size=1200):
    """Propagate through the actual filled stroke, keeping every reveal connected.

    Called with the separated S outline, so the drawing front follows S through
    the crossing instead of branching into the H stems. The original silhouette
    is restored by monogram_layers when the separately drawn letters combine.
    """
    svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'0 0 {V} {V}'})
    ET.SubElement(svg,'path',{'d':path,'fill':'white'})
    raster=Image.open(BytesIO(cairosvg.svg2png(bytestring=ET.tostring(svg),output_width=size,output_height=size))).convert('RGBA')
    mask=np.asarray(raster.getchannel('A'))>127
    points=np.argwhere(mask)
    ids=np.full(mask.shape,-1,dtype=np.int32)
    ids[mask]=np.arange(len(points),dtype=np.int32)
    rows=[];columns=[];costs=[]
    for dy,dx in [(0,1),(1,-1),(1,0),(1,1)]:
        a=ids[max(0,-dy):min(size,size-dy),max(0,-dx):min(size,size-dx)]
        b=ids[max(0,dy):min(size,size+dy),max(0,dx):min(size,size+dx)]
        connected=(a>=0)&(b>=0)
        rows.append(a[connected]);columns.append(b[connected])
        costs.append(np.full(np.count_nonzero(connected),math.hypot(dx,dy),dtype=np.float32))
    graph=coo_matrix((np.concatenate(costs),(np.concatenate(rows),np.concatenate(columns))),shape=(len(points),len(points))).tocsr()
    # Start inside the rounded upper-arc endpoint, in original SVG coordinates.
    seed=np.argmin(np.sum((points-np.array([105.,345.])*size/V)**2,axis=1))
    arrival=dijkstra(graph,directed=False,indices=seed)
    if not np.isfinite(arrival).all():raise ValueError('The main logo stroke must be connected')
    order=np.zeros(mask.shape,dtype=np.float32)
    order[mask]=arrival/arrival.max()
    # Extend to the exact vector boundary so side faces have no unfilled fringe.
    nearest=distance_transform_edt(~mask,return_distances=False,return_indices=True)
    order[~mask]=order[nearest[0][~mask],nearest[1][~mask]]
    return order,mask


def path_geometry(data):
    compound=None
    for subpath in parse_path(data).continuous_subpaths():
        points=[]
        for segment in subpath:
            count=max(2,int(math.ceil(segment.length()/1.5)))
            for t in np.linspace(0,1,count,endpoint=False):
                q=segment.point(t)
                points.append(((q.real-V/2)/180,(V/2-q.imag)/180))
        if len(points)<3:continue
        polygon=Polygon(points).buffer(0)
        compound=polygon if compound is None else compound.symmetric_difference(polygon)
    return compound


def geometry_mesh(compound):
    vertices=[]
    def vertex(p,z,n):
        x,y=p
        return [x,y,z,*n,(x*180+V/2)/V,(y*180+V/2)/V]
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


def logo_mesh(paths):
    return np.concatenate([geometry_mesh(path_geometry(p)) for p in paths])


def monogram_layers(paths):
    """Separate semantic S/H strokes while exactly retaining the source silhouette.

    Source path 8 flattens S together with the two upper H stems. Its actual
    S boundary is retained; two tangent-continuous boundary bridges close S where
    those stems branch off. H receives the remaining source pixels. The shared
    middle stroke belongs to S, while the source's interlacing gaps stay open.
    """
    p=parse_path(paths[8])
    def bridge(previous,following):
        start,end=previous.end,following.start
        length=abs(end-start)/3
        before,after=previous.derivative(1),following.derivative(0)
        return CubicBezier(start,start+before/abs(before)*length,
                           end-after/abs(after)*length,end)
    s_path=SVGPath(*list(p[3:6]),bridge(p[5],p[13]),*list(p[13:32]),bridge(p[31],p[3])).d()
    main=path_geometry(paths[8])
    s=path_geometry(s_path).intersection(main)
    upper_h=main.difference(s)
    pieces=list(upper_h.geoms) if isinstance(upper_h,MultiPolygon) else [upper_h]
    left=unary_union([g for g in pieces if g.centroid.x<0]+[path_geometry(paths[7])])
    right=unary_union([g for g in pieces if g.centroid.x>=0]+[path_geometry(paths[6])])
    expected=unary_union([main,path_geometry(paths[6]),path_geometry(paths[7])])
    combined=unary_union([s,left,right])
    if combined.symmetric_difference(expected).area>1e-9:
        raise ValueError('S/H decomposition changed the source logo silhouette')
    return s_path,s,left,right


def backdrop():
    yy,xx=np.mgrid[:H,:W]
    data=np.zeros((H,W,3))+[6,10,22]
    for x,y,s,c in [(1240,220,300,[24,9,53]),(1050,250,250,[0,12,24]),(450,150,600,[3,5,10])]:
        data+=np.exp(-((xx-x)**2+(yy-y)**2)/(2*s*s))[...,None]*c
    im=Image.fromarray(np.uint8(data),'RGB').convert('RGBA')
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
uniform sampler2D logo;uniform sampler2D bevel;uniform sampler2D revealMap;uniform mat4 model;
uniform float reveal;uniform float opacity;uniform int part;out vec4 color;
uniform vec2 strokeAxis;uniform vec2 strokeRange;
void main(){
 float drawingHead=0.;
 float coverage=1.;
 if(part>=8 && reveal<.9999){
   float order=part==8 ? texture(revealMap,uv).r :
     clamp((dot(uv,strokeAxis)-strokeRange.x)/(strokeRange.y-strokeRange.x),0.,1.);
   float feather=max(fwidth(order),.0008);
   coverage=1.-smoothstep(reveal-feather,reveal+feather,order);
   if(coverage<.001)discard;
   drawingHead=exp(-pow((order-reveal)/.012,2.));
 }
 vec3 bevelNormal=mat3(model)*(texture(bevel,uv).rgb*2.-1.);
 vec3 norm=normalize(mix(n,bevelNormal,step(.5,face))),view=normalize(vec3(0.,0.,7.2)-pos);
 vec3 light=normalize(vec3(-3.,4.,6.)-pos);
 float diffuse=max(dot(norm,light),0.);
 float spec=pow(max(dot(norm,normalize(light+view)),0.),80.);
 vec3 original=texture(logo,uv).rgb;
 vec3 front=original*(.88+.12*diffuse)+vec3(.18,.24,.3)*spec+vec3(.24,.40,.48)*drawingHead;
 float hue=clamp(uv.x*.6+(1.-uv.y)*.4,0.,1.);
 vec3 edge=mix(vec3(.14,.34,.50),vec3(.31,.13,.44),hue);
 vec3 side=edge*(.5+.7*diffuse)+vec3(.4,.5,.65)*spec;
 color=vec4(mix(side,front,step(.5,face)),opacity*coverage);
}
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');parser.add_argument('--frames',type=int,default=230)
    parser.add_argument('--output-dir',type=Path,default=ASSETS)
    args=parser.parse_args();paths,logo=logo_source();parts=[logo_mesh([p]) for p in paths]
    s_path,s_shape,h_left,h_right=monogram_layers(paths)
    output=args.output_dir;output.mkdir(parents=True,exist_ok=True)
    ctx=moderngl.create_standalone_context(require=330)
    print('Rendering original logo:',sum(len(p) for p in parts)//3,'triangles;',ctx.info['GL_RENDERER'],flush=True)
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
    reveal_order,_=stroke_reveal_field(s_path,logo.width)
    reveal_map=ctx.texture(logo.size,1,np.flipud(reveal_order).copy().tobytes(),dtype='f4')
    reveal_map.filter=(moderngl.LINEAR,moderngl.LINEAR)
    reveal_map.repeat_x=False;reveal_map.repeat_y=False
    reveal_map.use(2);prog['revealMap'].value=2
    vaos=[ctx.vertex_array(prog,[(ctx.buffer(p),'3f 3f 2f','in_pos','in_normal','in_uv')]) for p in parts]
    layer_vaos={i:ctx.vertex_array(prog,[(ctx.buffer(geometry_mesh(g)),'3f 3f 2f','in_pos','in_normal','in_uv')])
                for i,g in [(8,s_shape),(9,h_left),(10,h_right)]}
    axis=np.array([-.415,-.910]);axis/=np.linalg.norm(axis)
    prog['strokeAxis'].value=tuple(axis)
    stroke_ranges={}
    for i,g in [(9,h_left),(10,h_right)]:
        polygons=list(g.geoms) if isinstance(g,MultiPolygon) else [g]
        coords=np.concatenate([np.array(p.exterior.coords) for p in polygons])
        projected=(coords*180/V+.5)@axis
        stroke_ranges[i]=(float(projected.min()),float(projected.max()))
    f=1/math.tan(math.radians(36)/2)
    projection=np.array([[f/(SW/SH),0,0,0],[0,f,0,0],[0,0,-1.004,-.2004],[0,0,-1,0]])
    view=np.eye(4);view[2,3]=-7.2
    prog['vp'].write((projection@view).T.astype('f4').tobytes())
    samples=min(4,ctx.max_samples)
    ms=ctx.framebuffer(ctx.renderbuffer((SW,SH),components=4,samples=samples),ctx.depth_renderbuffer((SW,SH),samples=samples))
    fbo=ctx.simple_framebuffer((SW,SH),components=4);ctx.enable(moderngl.DEPTH_TEST)
    bg=backdrop();frames=[];count=1 if args.preview else args.frames
    poster_index=round(POSTER_MS*args.frames/LOOP_MS)
    for i in range(count):
        seconds=POSTER_MS/1000 if args.preview else i*LOOP_MS/(args.frames*1000)
        turn,fade=animation_state(seconds)
        base=rotation(turn+.06,'y')@rotation(.035,'x')
        ms.use();ms.clear(0,0,0,0)
        # During assembly S is one whole letter, and each H stem is one group
        # across the source's intentional interlacing gap. Once formed, use the
        # original unsplit geometry for the hold and complete 360-degree turn.
        forming=seconds<2.45
        sequence=[8,9,10,0,1,2,3,4,5] if forming else [8,7,6,0,1,2,3,4,5]
        for part_index in sequence:
            model=base.copy();reveal=1.;alpha=fade
            if forming and part_index==8:
                reveal=smoothstep((seconds-.10)/1.00)
                alpha*=smoothstep((seconds-.10)/.20)
            elif forming and part_index in (9,10):
                start=1.25 if part_index==9 else 1.35
                reveal=smoothstep((seconds-start)/.70)
                alpha*=smoothstep((seconds-start)/.15)
            elif forming:
                progress=smoothstep((seconds-(1.65+part_index*.07))/.32)
                offset=np.eye(4);offset[1,3]=-.32*(1-progress)
                model=base@offset;alpha*=progress
            if alpha<.001:continue
            prog['model'].write(model.T.astype('f4').tobytes())
            prog['part'].value=part_index;prog['reveal'].value=reveal;prog['opacity'].value=alpha
            prog['strokeRange'].value=stroke_ranges.get(part_index,(0.,1.))
            (layer_vaos[part_index] if forming and part_index>=8 else vaos[part_index]).render()
        ctx.copy_framebuffer(fbo,ms)
        scene=Image.frombytes('RGBA',(SW,SH),fbo.read(components=4,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        frame=bg.copy()
        glow=scene.filter(ImageFilter.GaussianBlur(20))
        glow.putalpha(glow.getchannel('A').point(lambda a:int(a*.18)))
        frame.alpha_composite(glow,(790,-40));frame.alpha_composite(scene,(790,-40))
        mask=Image.new('L',(W,H));ImageDraw.Draw(mask).rounded_rectangle((0,0,W-1,H-1),radius=24,fill=255)
        frame.putalpha(mask)
        if args.preview or i==poster_index: frame.save(output/'banner-static.png',optimize=True)
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
        frames[0].save(output/'banner.webp',format='WEBP',save_all=True,append_images=frames[1:],duration=durations,loop=0,lossless=True,method=4)
        indexed[0].save(output/'banner.gif',save_all=True,append_images=indexed[1:],duration=durations,loop=0,optimize=True,disposal=1)
        print('Lossless WebP bytes:',(output/'banner.webp').stat().st_size,flush=True)
        print('GIF bytes:',(output/'banner.gif').stat().st_size,flush=True)


if __name__=='__main__':main()
