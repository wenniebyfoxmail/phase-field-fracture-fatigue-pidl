function [gauss_pts, gauss_weights] = simplex_2d(quad_order)
%SIMPLEX_2D Native two-dimensional simplex quadrature used by S04-E011.

arguments
    quad_order (1,1) double {mustBeInteger,mustBePositive} = 2
end

if quad_order == 1
    gauss_pts = [1/3, 1/3];
    gauss_weights = 1/2;
elseif quad_order == 2
    % N=[1-xi-eta,xi,eta] gives barycentric order
    % (2/3,1/6,1/6), (1/6,2/3,1/6), (1/6,1/6,2/3).
    gauss_pts = [1/6, 1/6; 2/3, 1/6; 1/6, 2/3];
    gauss_weights = ones(3,1) / 6;
else
    error('phase_field:quadrature:UnsupportedE011Order', ...
        'S04-E011 supports simplex quadrature orders 1 and 2 only.');
end
end
