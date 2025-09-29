import numpy as np

def homography(src4, dst4):
    # src4, dst4: (4,2) float32 in (x,y) order. Returns 3x3 H with dst ~ H*src.
    A = []
    for (x,y),(X,Y) in zip(src4, dst4):
        A += [[x,y,1,0,0,0,-X*x,-X*y,-X],
              [0,0,0,x,y,1,-Y*x,-Y*y,-Y]]
    _,_,Vt = np.linalg.svd(np.asarray(A, np.float64))
    H = Vt[-1].reshape(3,3); return H / H[2,2]

def warp_perspective(src, dst_shape, quad):
    """
    src: HxWxC uint8 | float32, quad: 4 dst points (tl,tr,br,bl).
    Returns warped dst with bilinear sampling.
    """
    Hs, Ws = src.shape[:2]; Hd, Wd = dst_shape[:2]
    H = homography(np.array([[0,0],[Ws-1,0],[Ws-1,Hs-1],[0,Hs-1]], np.float32),
                   np.array(quad, np.float32))
    Hi = np.linalg.inv(H)
    y,x = np.meshgrid(np.arange(Hd), np.arange(Wd), indexing="ij")
    P = np.stack([x, y, np.ones_like(x)], -1).reshape(-1,3) @ Hi.T
    u = (P[:,0]/P[:,2]).reshape(Hd,Wd); v = (P[:,1]/P[:,2]).reshape(Hd,Wd)
    # bilinear sample
    u0 = np.clip(np.floor(u).astype(int), 0, Ws-2); v0 = np.clip(np.floor(v).astype(int), 0, Hs-2)
    du, dv = (u - u0)[...,None], (v - v0)[...,None]
    s00 = src[v0,   u0  ]; s10 = src[v0,   u0+1]
    s01 = src[v0+1, u0  ]; s11 = src[v0+1, u0+1]
    dst = (s00*(1-du)*(1-dv) + s10*du*(1-dv) + s01*(1-du)*dv + s11*du*dv)
    # mask out coords falling outside src
    ok = (u>=0)&(u<Ws-1)&(v>=0)&(v<Hs-1)
    out = np.zeros((Hd,Wd,src.shape[2]), src.dtype)
    out[ok] = dst[ok]
    return out

def soft_shadow(alpha, radius=6, offset=(8,8), color=(0,0,0), strength=0.6):
    """
    alpha: HxW float32 in [0,1] (layer mask). Returns RGB shadow image uint8.
    Separable three-box blur ≈ Gaussian; cheap + good enough.
    """
    def box_blur(a, r):
        pad = ((0,0),(r,r))
        tmp = np.pad(a, pad, mode='edge'); k = 2*r+1
        c = (np.cumsum(tmp,1)[:,k:] - np.cumsum(tmp,1)[:,:-k]) / k
        tmp = np.pad(c, pad, mode='edge')
        return (np.cumsum(tmp,0)[k:] - np.cumsum(tmp,0)[:-k]) / k

    r = max(1, int(radius))
    b = alpha.copy()
    for _ in range(3):  # stack of three boxes ≈ Gaussian
        b = box_blur(b, r)
    oy, ox = offset
    H, W = alpha.shape
    sh = np.zeros((H,W), np.float32)
    y0,y1 = max(0,oy), min(H, H+oy); x0,x1 = max(0,ox), min(W, W+ox)
    sy0,sy1 = y0-oy, y1-oy; sx0,sx1 = x0-ox, x1-ox
    sh[y0:y1, x0:x1] = b[sy0:sy1, sx0:sx1] * strength
    rgb = np.asarray(color, np.float32)[None,None,:]
    out = np.clip(sh[...,None] * rgb, 0, 255).astype(np.uint8)
    return out