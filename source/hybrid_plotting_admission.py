"""Dependency-only Agg render probe; no state, model or project data access."""
from io import BytesIO
import re


def probe_plotting(expected_version):
    if not isinstance(expected_version,str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)?',expected_version):
        raise RuntimeError('PLOTTING_VERSION_UNCONFIRMED: exact producer Matplotlib version must be confirmed and reviewed before execution')
    import matplotlib
    if matplotlib.__version__!=expected_version:
        raise RuntimeError(f'PLOTTING_VERSION_MISMATCH: expected {expected_version}, observed {matplotlib.__version__}')
    matplotlib.use('Agg',force=True)
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri
    if matplotlib.get_backend().lower()!='agg':raise RuntimeError('PLOTTING_BACKEND_MISMATCH: Agg required')
    fig=None
    try:
        # Exercise the full delivery's triangulation, gouraud, colourbar,
        # constrained-layout, text/font and both PNG/PDF paths on constants.
        tri=mtri.Triangulation([0.,1.,0.],[0.,0.,1.],[[0,1,2]])
        fig,ax=plt.subplots(figsize=(2,2),constrained_layout=True)
        artist=ax.tripcolor(tri,[0.,1.,.5],shading='gouraud',cmap='viridis',rasterized=True)
        fig.colorbar(artist,ax=ax);ax.set_title('Dependency probe');ax.set_xlabel('x')
        sizes={}
        for fmt,magic in [('png',b'\x89PNG\r\n\x1a\n'),('pdf',b'%PDF-')]:
            buf=BytesIO();fig.savefig(buf,format=fmt,dpi=40);data=buf.getvalue()
            if not data.startswith(magic):raise RuntimeError('PLOTTING_RENDER_FAILED: '+fmt)
            sizes[fmt]=len(data)
        return dict(completed=True,matplotlib=matplotlib.__version__,backend=matplotlib.get_backend(),
                    rendered_bytes=sizes,scope='constant triangle dependency probe only; no project state/model access')
    finally:
        if fig is not None:plt.close(fig)
