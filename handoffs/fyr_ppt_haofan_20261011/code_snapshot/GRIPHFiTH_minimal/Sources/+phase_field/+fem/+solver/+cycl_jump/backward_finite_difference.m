function [dpf_dxp] = backward_finite_difference(f_i,p)
%BACKWARD_FINITE_DIFFERENCE compute the backard finite difference approximation of the p.th derivative of f with respect to x based on n equidistant points f_i
%
%   f_i     discrete points of f, might be scalar/ vector/ matrix
%           given as struct, i.e. f_i = {f(x-2) f(x-1) f(x)}
%   p       p.th derivative which shall be approximated

% Copyright (C) 2021 ETH Zurich, SIS ID and CompMech D-MAVT
%
% Licensed under the Apache License, Version 2.0 (the "License");
% you may not use this file except in compliance with the License.
% You may obtain a copy of the License at
%
%    http://www.apache.org/licenses/LICENSE-2.0
%
% Unless required by applicable law or agreed to in writing, software
% distributed under the License is distributed on an "AS IS" BASIS,
% WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
% See the License for the specific language governing permissions and
% limitations under the License.

%get size of stencil (how many discrete points of f are given)
n = length(f_i);

%switch between n to determine finite difference quotient
switch n

    % =======================================================================
    %stencil: f(x-2), f(x-1), f(x)
    case 3
        
        %switch between the p.th derivative
        switch p

            case 1
                dpf_dxp = (f_i{1} - 4*f_i{2} + 3*f_i{3})/2;

            case 2
                dpf_dxp = f_i{1} - 2*f_i{2} + f_i{3};

            otherwise
                error('finite difference approximation is only available for first and second derivative for stencil of three points');
            
        end

    % =======================================================================
    %stencil: f(x-3), f(x-2), f(x-1), f(x)
    case 4

        %switch between the p.th derivative
        switch p

            case 1
                dpf_dxp = (-2*f_i{1} + 9*f_i{2} - 18*f_i{3} + 11*f_i{4})/6;

            case 2
                dpf_dxp = -f_i{1} + 4*f_i{2} - 5*f_i{3} + 2*f_i{4};

            case 3
                dpf_dxp = -f_i{1} + 3*f_i{2} - 3*f_i{3} + f_i{4};

            otherwise
                error('finite difference approximation is only available for up to third derivative for stencil of four points');
            
        end
    
    % =======================================================================
    %stencil: f(x-4), f(x-3), f(x-2), f(x-1), f(x)
    case 5

        %switch between the p.th derivative
        switch p

            case 1
                dpf_dxp = (3*f_i{1} - 16*f_i{2} + 36*f_i{3} - 48*f_i{4} + 25*f_i{5})/12;

            case 2
                dpf_dxp = (11*f_i{1} - 56*f_i{2} + 114*f_i{3} - 104*f_i{4} + 35*f_i{5})/12;
                
            case 3
                dpf_dxp = (3*f_i{1} - 14*f_i{2} + 24*f_i{3} - 18*f_i{4} + 5*f_i{5})/2;
                
            case 4
                dpf_dxp = f_i{1} - 4*f_i{2} + 6*f_i{3} - 4*f_i{4} + f_i{5};

            otherwise
                error('finite difference approximation is only available for up to fourth derivative for stencil of five points');
                
        end

    % =======================================================================
    %stencil: f(x-5), f(x-4), f(x-3), f(x-2), f(x-1), f(x)
    case 6

        %switch between the p.th derivative
        switch p

            case 1
                dpf_dxp = (-12*f_i{1} + 75*f_i{2} - 200*f_i{3} + 300*f_i{4} - 300*f_i{5} + 137*f_i{6})/60;
                
            case 2
                dpf_dxp = (-10*f_i{1} + 61*f_i{2} - 156*f_i{3} + 214*f_i{4} - 154*f_i{5} + 45*f_i{6})/12;
                
            case 3
                dpf_dxp = (-7*f_i{1} + 41*f_i{2} - 98*f_i{3} + 118*f_i{4} - 71*f_i{5} + 17*f_i{6})/4;
                
            case 4
                dpf_dxp = -2*f_i{1} + 11*f_i{2} - 24*f_i{3} + 26*f_i{4} - 14*f_i{5} + 3*f_i{6};

            otherwise
                error('finite difference approximation is only available for up to fourth derivative for stencil of six points');
                
        end
        
    % =======================================================================
    %arbitrary stencil, based on:
    % Taylor (2016), 'Finite Difference Coefficients Calculator', (https://web.media.mit.edu/~crtaylor/calculator.html)
    otherwise

        stencil = -(n-1):0;
        A = zeros(n);
        b=zeros(n,1);
        
        %compute matrix A
        for row=1:n
            for col=1:n
                A(row,col) = stencil(col)^(row-1);
            end
        end
        
        %compute vector b
        b(p+1)=factorial(p);
        
        %compute coefficients
        c = A\b;

        %compute derivative
        dpf_dxp = 0;
        for j=1:n
            dpf_dxp = dpf_dxp + c(j)*f_i{j};
        end

end
