"""
Generate a bunch of trimesh objects, in meter radian
"""

import math
import numpy as np
import basis.trimesh.primitives as tp
import basis.trimesh as trm
import basis.robotmath as rm
import shapely.geometry as shpg


def gen_box(extent=np.array([1, 1, 1]), homomat=np.eye(4)):
    """
    :param extent: x, y, z (origin is 0)
    :param homomat: rotation and translation
    :return: a Trimesh object (Primitive)
    author: weiwei
    date: 20191228osaka
    """
    return tp.Box(box_extents=extent, box_transform=homomat)


def gen_stick(spos=np.array([0, 0, 0]), epos=np.array([0.1, 0, 0]), thickness=0.005, type="rect", sections=8):
    """
    interface to genrectstick/genroundstick
    :param spos: 1x3 nparray
    :param epos: 1x3 nparray
    :param thickness: 0.005 m by default
    :param type: simple or smooth
    :param sections: # of discretized sectors used to approximate a cylinder
    :return:
    author: weiwei
    date: 20191228osaka
    """
    if type == "rect":
        return gen_rectstick(spos, epos, thickness, sections=sections)
    if type == "round":
        return gen_roundstick(spos, epos, thickness, count=[sections / 2.0, sections / 2.0])


def gen_rectstick(spos=np.array([0, 0, 0]), epos=np.array([0.1, 0, 0]), thickness=.005, sections=8):
    """
    :param spos: 1x3 nparray
    :param epos: 1x3 nparray
    :param thickness: 0.005 m by default
    :param sections: # of discretized sectors used to approximate a cylinder
    :return: a Trimesh object (Primitive)
    author: weiwei
    date: 20191228osaka
    """
    pos = spos
    height = np.linalg.norm(epos - spos)
    if np.allclose(height, 0):
        rotmat = np.eye(3)
    else:
        rotmat = rm.rotmat_between_vectors(np.array([0, 0, 1]), epos - spos)
    homomat = rm.homomat_from_posrot(pos, rotmat)
    return tp.Cylinder(height=height, radius=thickness / 2.0, sections=sections, homomat=homomat)


def gen_roundstick(spos=np.array([0, 0, 0]), epos=np.array([0.1, 0, 0]), thickness=0.005, count=[8, 8]):
    """
    :param spos:
    :param epos:
    :param thickness:
    :return: a Trimesh object (Primitive)
    author: weiwei
    date: 20191228osaka
    """
    pos = spos
    height = np.linalg.norm(epos - spos)
    if np.allclose(height, 0):
        rotmat = np.eye(3)
    else:
        rotmat = rm.rotmat_between_vectors(np.array([0, 0, 1]), epos - spos)
    homomat = rm.homomat_from_posrot(pos, rotmat)
    return tp.Capsule(height=height, radius=thickness / 2.0, count=count, homomat=homomat)


def gen_sphere(pos=np.array([0, 0, 0]), radius=0.02, subdivisions=2):
    """
    :param pos: 1x3 nparray
    :param radius: 0.02 m by default
    :param subdivisions: levels of icosphere discretization
    :return:
    author: weiwei
    date: 20191228osaka
    """
    return tp.Sphere(sphere_radius=radius, sphere_center=pos, subdivisions=subdivisions)


def gen_ellipsoid(pos=np.array([0, 0, 0]), axmat=np.eye(3), subdivisions=5):
    """
    :param pos:
    :param axmat: 3x3 mat, each column is an axis of the ellipse
    :param subdivisions: levels of icosphere discretization
    :return:
    author: weiwei
    date: 20191228osaka
    """
    homomat = rm.homomat_from_posrot(pos, axmat)
    sphere = tp.Sphere(sphere_radius=1, sphere_center=pos, subdivisions=subdivisions)
    vertices = rm.homomat_transform_points(homomat, sphere.vertices)
    return trm.Trimesh(vertices=vertices, faces=sphere.faces)


def gen_dumbbell(spos=np.array([0, 0, 0]), epos=np.array([0.1, 0, 0]), thickness=0.005, sections=8, subdivisions=1):
    """
    :param spos: 1x3 nparray
    :param epos: 1x3 nparray
    :param thickness: 0.005 m by default
    :param sections:
    :param subdivisions: levels of icosphere discretization
    :return:
    author: weiwei
    date: 20191228osaka
    """
    stick = gen_rectstick(spos=spos, epos=epos, thickness=thickness, sections=sections)
    sposball = gen_sphere(pos=spos, radius=thickness, subdivisions=subdivisions)
    endball = gen_sphere(pos=epos, radius=thickness, subdivisions=subdivisions)
    vertices = np.array(stick.vertices.tolist()+sposball.vertices.tolist()+endball.vertices.tolist())
    sposballfaces = sposball.faces + len(stick.vertices)
    endballfaces = endball.faces + len(sposball.vertices) + len(stick.vertices)
    faces = np.array(stick.faces.tolist()+sposballfaces.tolist()+endballfaces.tolist())
    return trm.Trimesh(vertices=vertices, faces=faces)


def gen_cone(spos=np.array([0, 0, 0]), epos=np.array([0.1, 0, 0]), radius=0.005, sections=8):
    """
    :param spos: 1x3 nparray
    :param epos: 1x3 nparray
    :param thickness: 0.005 m by default
    :param sections: # of discretized sectors used to approximate a cylinder
    :return:
    author: weiwei
    date: 20191228osaka
    """
    height = np.linalg.norm(spos - epos)
    pos = spos
    rotmat = rm.rotmat_between_vectors(np.array([0, 0, 1]), epos - spos)
    homomat = rm.homomat_from_posrot(pos, rotmat)
    return tp.Cone(height=height, radius=radius, sections=sections, homomat=homomat)


def gen_arrow(spos=np.array([0, 0, 0]), epos=np.array([0.1, 0, 0]), thickness=0.005, sections=8, sticktype="rect"):
    """
    :param spos: 1x3 nparray
    :param epos: 1x3 nparray
    :param thickness: 0.005 m by default
    :param sections: # of discretized sectors used to approximate a cylinder
    :param sticktype: The shape at the end of the arrow stick, round or rect
    :param radius:
    :return:
    author: weiwei
    date: 20191228osaka
    """
    direction = rm.unit_vector(epos - spos)
    stick = gen_stick(spos=spos, epos=epos - direction * thickness * 4, thickness=thickness, type=sticktype,
                     sections=sections)
    cap = gen_cone(spos=epos - direction * thickness * 4, epos=epos, radius=thickness, sections=sections)
    vertices = np.array(stick.vertices.tolist()+cap.vertices.tolist())
    capfaces = cap.faces + len(stick.vertices)
    faces = np.array(stick.faces.tolist()+capfaces.tolist())
    return trm.Trimesh(vertices=vertices, faces=faces)


def gen_dasharrow(spos=np.array([0, 0, 0]), epos=np.array([0.1, 0, 0]), thickness=0.005, lsolid=None, lspace=None,
                 sections=8, sticktype="rect"):
    """
    :param spos: 1x3 nparray
    :param epos: 1x3 nparray
    :param thickness: 0.005 m by default
    :param lsolid: length of the solid section, 1*thickness if None
    :param lspace: length of the empty section, 1.5*thickness if None
    :return:
    author: weiwei
    date: 20191228osaka
    """
    solidweight = 1.6
    spaceweight = 1.07
    totalweight = solidweight + spaceweight
    if not lsolid:
        lsolid = thickness * solidweight
    if not lspace:
        lspace = thickness * spaceweight
    length, direction = rm.unit_vector(epos - spos, togglelength=True)
    nstick = math.floor(length / (thickness * totalweight))
    cap = gen_cone(spos=epos - direction * thickness * 4, epos=epos, radius=thickness, sections=sections)
    stick = gen_stick(spos=epos - direction * thickness * 4 - lsolid * direction, epos=epos - direction * thickness * 4,
                     thickness=thickness, type=sticktype, sections=sections)
    vertices_list = cap.vertices.tolist()+stick.vertices.tolist()
    stickfaces = stick.faces + len(cap.vertices)
    faces_list = cap.faces.tolist()+stickfaces.tolist()
    for i in range(1, nstick - 1):
        tmpspos = epos - direction * thickness * 4 - lsolid * direction - (lsolid * direction + lspace * direction) * i
        tmpstick = gen_stick(spos=tmpspos, epos=tmpspos + lsolid * direction, thickness=thickness, type=sticktype,
                            sections=sections)
        tmpstickfaces = tmpstick.faces + len(vertices_list)
        vertices_list += tmpstick.vertices.tolist()
        faces_list += tmpstickfaces.tolist()
    return trm.Trimesh(vertices=np.array(vertices_list), faces=np.array(faces_list))


def gen_axis(pos=np.array([0, 0, 0]), rotmat=np.eye(3), length=0.1, thickness=0.005):
    """
    :param spos: 1x3 nparray
    :param epos: 1x3 nparray
    :param thickness: 0.005 m by default
    :return:
    author: weiwei
    date: 20191228osaka
    """
    directionx = rotmat[:, 0]
    directiony = rotmat[:, 1]
    directionz = rotmat[:, 2]
    # x
    endx = directionx * length
    stickx = gen_stick(spos=pos, epos=endx, thickness=thickness)
    capx = gen_cone(spos=endx, epos=endx + directionx * thickness * 4, radius=thickness)
    # y
    endy = directiony * length
    sticky = gen_stick(spos=pos, epos=endy, thickness=thickness)
    capy = gen_cone(spos=endy, epos=endy + directiony * thickness * 4, radius=thickness)
    # z
    endz = directionz * length
    stickz = gen_stick(spos=pos, epos=endz, thickness=thickness)
    capz = gen_cone(spos=endz, epos=endz + directionz * thickness * 4, radius=thickness)
    vertices = np.array(stickx.vertices.tolist()+capx.vertices.tolist()+
                        sticky.vertices.tolist()+capy.vertices.tolist()+
                        stickz.vertices.tolist()+capz.vertices.tolist())
    capxfaces = capx.faces + len(stickx.vertices)
    stickyfaces = sticky.faces + len(stickx.vertices) + len(capx.vertices)
    capyfaces = capy.faces + len(stickx.vertices) + len(capx.vertices) + len(sticky.vertices)
    stickzfaces = stickz.faces + len(stickx.vertices) + len(capx.vertices) + len(sticky.vertices) + len(capy.vertices)
    capzfaces = capz.faces + len(stickx.vertices) + len(capx.vertices) + len(sticky.vertices) + len(
        capy.vertices) + len(stickz.vertices)
    faces = np.array(stickx.faces.tolist()+capxfaces.tolist()+
                     stickyfaces.tolist()+capyfaces.tolist()+
                     stickzfaces.tolist()+capzfaces.tolist())
    return trm.Trimesh(vertices=vertices, faces=faces)


def gen_torus(axis=np.array([1, 0, 0]), portion=.5, center=np.array([0, 0, 0]), radius=0.005, thickness=0.0015,
             sections=8, discretization=24):
    """
    :param axis: the circ arrow will rotate around this axis 1x3 nparray
    :param portion: 0.0~1.0
    :param center: the center position of the circ 1x3 nparray
    :param radius:
    :param thickness:
    :param sections: # of discretized sectors used to approximate a cylindrical stick
    :param discretization: number sticks used for approximating a torus
    :return:
    author: weiwei
    date: 20200602
    """
    unitaxis = rm.unit_vector(axis)
    startingaxis = rm.orthogonal_vector(unitaxis)
    startingpos = startingaxis * radius + center
    discretizedangle = 2 * math.pi / discretization
    ndist = int(portion * discretization)
    # gen the last sec first
    # gen the remaining torus afterwards
    if ndist > 0:
        lastpos = center + np.dot(rm.rotmat_from_axangle(unitaxis, (ndist - 1) * discretizedangle),
                                  startingaxis) * radius
        nxtpos = center + np.dot(rm.rotmat_from_axangle(unitaxis, ndist * discretizedangle), startingaxis) * radius
        stick = gen_stick(spos=lastpos, epos=nxtpos, thickness=thickness, sections=sections, type="round")
        vertices_list = stick.vertices.tolist()
        faces_list = stick.faces.tolist()
        lastpos = startingpos
        for i in range(1 * np.sign(ndist), ndist, 1 * np.sign(ndist)):
            nxtpos = center + np.dot(rm.rotmat_from_axangle(unitaxis, i * discretizedangle), startingaxis) * radius
            stick = gen_stick(spos=lastpos, epos=nxtpos, thickness=thickness, sections=sections, type="round")
            stickfaces = stick.faces + len(vertices_list)
            vertices_list += stick.vertices.tolist()
            faces_list += stickfaces.tolist()
            lastpos = nxtpos
        return trm.Trimesh(vertices=np.array(vertices_list), faces=np.array(faces_list))
    else:
        return trm.Trimesh()


def gen_circarrow(axis=np.array([1, 0, 0]), portion=0.3, center=np.array([0, 0, 0]), radius=0.005, thickness=0.0015,
                  sections=8, discretization=24):
    """
    :param axis: the circ arrow will rotate around this axis 1x3 nparray
    :param portion: 0.0~1.0
    :param center: the center position of the circ 1x3 nparray
    :param radius:
    :param thickness:
    :param rgba:
    :param discretization: number sticks used for approximation
    :return:
    author: weiwei
    date: 20200602
    """
    unitaxis = rm.unit_vector(axis)
    startingaxis = rm.orthogonal_vector(unitaxis)
    startingpos = startingaxis * radius + center
    discretizedangle = 2 * math.pi / discretization
    ndist = int(portion * discretization)
    # gen the last arrow first
    # gen the remaining torus
    if ndist > 0:
        lastpos = center + np.dot(rm.rotmat_from_axangle(unitaxis, (ndist - 1) * discretizedangle),
                                  startingaxis) * radius
        nxtpos = center + np.dot(rm.rotmat_from_axangle(unitaxis, ndist * discretizedangle), startingaxis) * radius
        arrow = gen_arrow(spos=lastpos, epos=nxtpos, thickness=thickness, sections=sections, sticktype="round")
        vertices_list = arrow.vertices.tolist()
        faces_list = arrow.faces.tolist()
        lastpos = startingpos
        for i in range(1 * np.sign(ndist), ndist, 1 * np.sign(ndist)):
            nxtpos = center + np.dot(rm.rotmat_from_axangle(unitaxis, i * discretizedangle), startingaxis) * radius
            stick = gen_stick(spos=lastpos, epos=nxtpos, thickness=thickness, sections=sections, type="round")
            stickfaces = stick.faces + len(vertices_list)
            vertices_list += stick.vertices.tolist()
            faces_list += stickfaces.tolist()
            lastpos = nxtpos
        return trm.Trimesh(vertices=np.array(vertices_list), faces=np.array(faces_list))
    else:
        return trm.Trimesh()


def facet_boundary(objtrimesh, facet, facetcenter, facetnormal):
    """
    compute a boundary polygon for facet
    assumptions:
    1. there is only one boundary
    2. the facet is convex
    :param objtrimesh: a datatype defined in trimesh
    :param facet: a data type defined in trimesh
    :param facetcenter and facetnormal used to compute the transform, see trimesh.geometry.plane_transform
    :return: [1x3 vertices list, 1x2 vertices list, 4x4 homogeneous transformation matrix)]
    author: weiwei
    date: 20161213tsukuba
    """
    facetp = None
    # use -facetnormal to let the it face downward
    facethomomat = trm.geometry.plane_transform(facetcenter, -facetnormal)
    for i, faceidx in enumerate(facet):
        vert0 = objtrimesh.vertices[objtrimesh.faces[faceidx][0]]
        vert1 = objtrimesh.vertices[objtrimesh.faces[faceidx][1]]
        vert2 = objtrimesh.vertices[objtrimesh.faces[faceidx][2]]
        vert0p = rm.homotransformpoint(facethomomat, vert0)
        vert1p = rm.homotransformpoint(facethomomat, vert1)
        vert2p = rm.homotransformpoint(facethomomat, vert2)
        facep = shpg.Polygon([vert0p[:2], vert1p[:2], vert2p[:2]])
        if facetp is None:
            facetp = facep
        else:
            facetp = facetp.union(facep)
    verts2d = list(facetp.exterior.coords)
    verts3d = []
    for vert2d in verts2d:
        vert3d = rm.homotransformpoint(rm.homoinverse(facethomomat), np.array([vert2d[0], vert2d[1], 0]))[:3]
        verts3d.append(vert3d)
    return verts3d, verts2d, facethomomat


if __name__ == "__main__":
    import visualization.panda.world as wd
    import modeling.collisionmodel as cm
    base = wd.World(campos=[.1, 0, 0], lookatpos=[0, 0, 0], autocamrotate=False)
    objcm = cm.CollisionModel(gen_torus())
    objcm.set_rgba([1, 0, 0, 1])
    objcm.attach_to(base)
    objcm = cm.CollisionModel(gen_axis())
    objcm.set_rgba([1, 0, 0, 1])
    objcm.attach_to(base)
    base.run()
