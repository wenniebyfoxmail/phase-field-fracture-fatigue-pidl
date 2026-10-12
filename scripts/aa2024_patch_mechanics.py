"""Small normalized static CST patch kernel; no phase-field evolution law.

Real-data solves belong on the frozen producer after independent review. Local
tests use tiny synthetic patches only. Damage is fixed during each static solve.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


def rectangular_mesh(nx=41, ny=21, width=36., height=18.):
    if nx < 2 or ny < 2 or nx * ny > 2000:
        raise ValueError("mesh budget/dimensions")
    x, y = np.meshgrid(np.linspace(-width/2, width/2, nx),
                       np.linspace(-height/2, height/2, ny))
    xy = np.c_[x.ravel(), y.ravel()]
    triangles = []
    for j in range(ny-1):
        for i in range(nx-1):
            a = j*nx+i
            triangles += [[a, a+1, a+nx+1], [a, a+nx+1, a+nx]]
    boundary = np.zeros(nx*ny, dtype=bool)
    boundary[:nx] = boundary[-nx:] = True
    boundary[::nx] = boundary[nx-1::nx] = True
    return xy, np.asarray(triangles, dtype=int), boundary


def candidate_basis(xy):
    # Training-derived modeling prior, NOT independently measured crack geometry.
    delta_x = np.maximum(np.maximum(-9.-xy[:, 0], xy[:, 0]-6.), 0)
    distance = np.sqrt(delta_x**2 + xy[:, 1]**2)
    d0 = np.exp(-distance/1.5)
    b = np.exp(-((xy[:, 0]-6.)**2 + xy[:, 1]**2)/(2*3.**2))
    return d0, b


def stiffness(xy, triangles, damage, *, E=1., nu=.30):
    xy, tri, damage = np.asarray(xy), np.asarray(triangles), np.asarray(damage)
    if (xy.ndim != 2 or xy.shape[1] != 2 or damage.shape != (len(xy),) or
        tri.ndim != 2 or tri.shape[1] != 3 or
        not np.isfinite(xy).all() or not np.isfinite(damage).all() or
        np.any(damage < 0) or np.any(damage > 1) or
        not np.isfinite(E) or E <= 0 or not -.99 < nu < .49):
        raise ValueError("invalid mechanics inputs")
    if not np.issubdtype(tri.dtype, np.integer) or np.any(tri < 0) or np.any(tri >= len(xy)):
        raise ValueError("invalid triangle indices")
    D = E/(1-nu**2)*np.array([[1,nu,0],[nu,1,0],[0,0,(1-nu)/2]])
    rr, cc, vv = [], [], []
    for nodes in tri:
        p = xy[nodes]
        twice_area = ((p[1,0]-p[0,0])*(p[2,1]-p[0,1]) -
                      (p[1,1]-p[0,1])*(p[2,0]-p[0,0]))
        if twice_area <= 1e-12:
            raise ValueError("nonpositive/degenerate element area")
        dx = np.array([p[1,1]-p[2,1], p[2,1]-p[0,1], p[0,1]-p[1,1]])/twice_area
        dy = np.array([p[2,0]-p[1,0], p[0,0]-p[2,0], p[1,0]-p[0,0]])/twice_area
        B = np.zeros((3,6))
        B[0,0::2] = dx
        B[1,1::2] = dy
        B[2,0::2] = dy
        B[2,1::2] = dx
        # Frozen quadrature approximation: degradation of mean nodal damage.
        g = (1-float(damage[nodes].mean()))**2 + 1e-6
        ke = .5*twice_area*g*(B.T@D@B)
        dofs = np.column_stack((2*nodes,2*nodes+1)).ravel()
        rr.extend(np.repeat(dofs,6)); cc.extend(np.tile(dofs,6)); vv.extend(ke.ravel())
    return coo_matrix((vv,(rr,cc)),shape=(2*len(xy),2*len(xy))).tocsr()


def solve_patch(xy, triangles, boundary, boundary_values, damage, *, E=1., nu=.30):
    boundary = np.asarray(boundary, dtype=bool)
    values = np.asarray(boundary_values, dtype=float)
    if boundary.shape != (len(xy),) or values.shape != (boundary.sum(),2) or not np.isfinite(values).all():
        raise ValueError("boundary shape/values")
    if not boundary.any() or boundary.all():
        raise ValueError("requires boundary and interior")
    K = stiffness(xy,triangles,damage,E=E,nu=nu)
    fixed = np.flatnonzero(np.repeat(boundary,2))
    free = np.flatnonzero(~np.repeat(boundary,2))
    u = np.zeros(2*len(xy)); u[fixed] = values.ravel()
    rhs = -(K[free][:,fixed]@u[fixed])
    u[free] = spsolve(K[free][:,free],rhs)
    if not np.isfinite(u).all():
        raise ValueError("nonfinite static solve")
    residual = K[free]@u
    relative = np.linalg.norm(residual)/max(np.linalg.norm(rhs),1e-15)
    if relative > 1e-8:
        raise ValueError("static residual failure")
    return u.reshape(-1,2), float(relative)


def sample_regular_mesh(values, xy, *, nx=41, ny=21, width=36., height=18.):
    """Frozen diagonal CST interpolation; exactly reproduces affine fields."""
    p = np.asarray(xy)
    if p.ndim != 2 or p.shape[1] != 2 or not np.isfinite(p).all():
        raise ValueError("sampling coordinates")
    x = (p[:,0]+width/2)/width*(nx-1)
    y = (p[:,1]+height/2)/height*(ny-1)
    if np.any(x < 0) or np.any(x > nx-1) or np.any(y < 0) or np.any(y > ny-1):
        raise ValueError("sampling outside frozen domain")
    i = np.minimum(np.floor(x).astype(int),nx-2)
    j = np.minimum(np.floor(y).astype(int),ny-2)
    fx,fy = x-i,y-j
    a = j*nx+i
    lower = fy <= fx
    indices = np.column_stack((a, np.where(lower,a+1,a+nx+1),
                                np.where(lower,a+nx+1,a+nx)))
    weights = np.column_stack((1-np.where(lower,fx,fy),
                                np.where(lower,fx-fy,fx),
                                np.where(lower,fy,fy-fx)))
    return np.einsum('ni,nij->nj',weights,np.asarray(values)[indices])
