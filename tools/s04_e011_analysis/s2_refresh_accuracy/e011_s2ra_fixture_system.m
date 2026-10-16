classdef e011_s2ra_fixture_system < handle
 % Tiny source-Newton fixture only; no native FEM/MEX field assembly.
 properties
  MESH=[]
  DOFS=[]
  GEOM=struct('t',1)
  QUADRATURE=[]
  MAT_CHAR=[]
  CC=[]
  stress_state=struct('as_number',0)
  STIFFNESS_MATRIX=struct('i_row',1,'j_col',1)
 end
end
