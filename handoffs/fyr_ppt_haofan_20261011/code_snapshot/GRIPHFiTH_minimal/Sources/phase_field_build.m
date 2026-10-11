function [] = phase_field_build(args)
%PHASE_FIELD_BUILD Build phase_field namespace mexFunctions.
%
%  The following keyword arguments can be set, otherwise, are set with default values:
%
%       debug = false;  % Disable bytecode optimization and enable extra checks
%       arch_native = false;  % Optimize code for native architecture (only if not
%                             % in debug build);
%                             % BEWARE: increases numerical differences or may even
%                             % break eniterly compilation (observed for
%                             % Intel(R) Core(TM) i9-9880H on macOS 11.6.4 with
%                             % MATLAB R2020b and ifort 19.1.0)
%

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

arguments
    args.debug (1, 1) logical = false
    args.arch_native (1, 1) logical = false
end

matlab_min_version = '9.7';
matlab_min_release = '(R2019b)';  % Beware: manually keep in-sync w/ above

if (verLessThan('matlab', matlab_min_version))
    v = ver('matlab');
    error(...
        'Minimal supported MATLAB version is %s %s, whereas you are using %s %s %s',...
        matlab_min_version, matlab_min_release, v.Name, v.Version, v.Release);
end

mac = ismac;
linux = isunix && ~mac;
is64 = contains(computer, '64');

mex_fortran_nfo = evalc('mex(''-setup'', ''FORTRAN'')');
gfortran = contains(mex_fortran_nfo, 'gfortran');
ifort = contains(mex_fortran_nfo, 'ifort') || contains(mex_fortran_nfo, 'Intel');
assert(xor(gfortran, ifort));

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% MEX flags
mflags = '' ;

% % use large-array-handling API on a 64-bit platform
% if (is64)
%     mflags = '-largeArrayDims';
% end

% silent
mflags = ['-silent ', mflags];

% LAPACK and BLAS
lapack = '-lmwlapack -lmwblas';
% POSIX timing routine
if (linux)
    lapack = [lapack, ' -lrt'];
end
mflags = sprintf('%s %s', mflags, lapack);

% 64-bit BLAS on a 64-bit platform
if (is64)
    mflags = [mflags, ' -DBLAS64'];
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Compiler flags
fflags = '';
compflags = '';  % Windows-only
foptimflags = '';

if (gfortran)
    fflags = [fflags, ' -cpp -ffree-line-length-none'];
else  % ifort
    if (mac)
        fflags = [fflags, ' -free'];
    end
    compflags = [compflags, ' /free'];
end

% Checks
%
% Compile with all warnings: -Wall -Wextra
%    * BEWARE: -Wpedantic does not work well with MEX interface integer types (mwSize etc)
%    * ifort: -warn all


if (gfortran)
    fflags = [fflags, ' -Wall -Wextra -Werror'];
else  % ifort
    if (mac)
    fflags = [fflags, ' -warn all -warn noexternal -warn errors'];
    end
    compflags = [compflags, ' /warn:all /warn:noexternals /warn:errors'];
end

% Optimization

if (args.debug)
% A) For debugging:
%
% 1. Compile with runtime checks (reduces runtime performance):
%    Check, the size of arrays at runtime (Fortran guarantee): -fcheck=bounds
%    * Note: for more checks use -fcheck=all
%    * ifort: -check all / -check bounds
%    See https://www.intel.com/content/www/us/en/develop/documentation/fortran-compiler-oneapi-dev-guide-and-reference/top/compiler-reference/compiler-options/compiler-option-details/language-options/check.html
%
% 2. Compile without optimization: -O0
%    * with ifort on unix also no inline expansion of stdlib intrinsics: -nolib-inline
% 3. Compile with sanitizers to check for memory leaks or for undefined behaviour:
%    -fsanitize=address (same for linking) or -fsanitize=undefined (and -lubsan for
%    linking)
%    * BEWARE: requires an independent backend to be actually useful; does not work well
%      when going over MATLAB.

    if (gfortran)
        fflags = [fflags, ' -fcheck=bounds'];
    else  % ifort
        if (mac)
            fflags = [fflags, ' -check bounds -nolib-inline'];
        end
        compflags = [compflags, ' /check bounds'];
    end
    foptimflags = [foptimflags, ' -O0'];

else
% B) For preformance, it's recommended to use:
%
% * with the Intel compilers: -xHost and -O2 or higher,
% * with the GNU compilers: -march=native and -O3.
%
% Note: default used by MEX is -O2, compiler-independent; however, vectorization is
% enabled with -O2 for ifort, but only with -O3 for gfortran (cf. -ftree-vectorize).

    if (gfortran)
        foptimflags = [foptimflags, ' -O3'];
        if (args.arch_native)
            foptimflags = [foptimflags, ' -march=native'];
        end
    else  % ifort
        foptimflags = [foptimflags, ' -O2'];
        if (args.arch_native)
            if (mac)
                foptimflags = [foptimflags, ' -xHost'];
            end
            compflags =  [compflags, ' /QxHost'];
        end
    end
end

fflags = sprintf('FFLAGS="$FFLAGS %s"', fflags);
compflags = sprintf('COMPFLAGS="$COMPFLAGS %s"', compflags);
foptimflags = sprintf('FOPTIMFLAGS="%s"', foptimflags); % hard override default: "-O2"

cflags = sprintf('%s %s %s', fflags, compflags, foptimflags);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% MEX sources
sources_dir = fileparts(which('phase_field_build'));
mex_sources_dir = fullfile(sources_dir, '+phase_field', '+mex');

mex_sources = {
    './+fem/+assembly/+equilibrium/initial.f90', ...
    './+fem/+assembly/+equilibrium/AMOR.f90', ...
    './+fem/+assembly/+equilibrium/FREDDI.f90', ...
    './+fem/+assembly/+equilibrium/ISO.f90', ...
    './+fem/+assembly/+equilibrium/MIEHE.f90', ...
    './+fem/+assembly/+equilibrium/PF_CZM.f90', ...
    './+fem/+assembly/+pf/AT1_HISTORY.f90', ...
    './+fem/+assembly/+pf/AT1_PENALTY.f90', ...
    './+fem/+assembly/+pf/AT2_HISTORY.f90', ...
    './+fem/+assembly/+pf/AT2_PENALTY.f90', ...
    './+fem/+assembly/+pf/AT1_HISTORY_FATIGUE.f90', ...
    './+fem/+assembly/+pf/AT1_PENALTY_FATIGUE.f90', ...
    './+fem/+assembly/+pf/AT2_HISTORY_FATIGUE.f90', ...
    './+fem/+assembly/+pf/AT2_PENALTY_FATIGUE.f90', ...
    './+fem/+assembly/+pf/PF_CZM_HISTORY_FATIGUE.f90', ...
    './+fem/+processing/fracture_energy.f90', ...
    './+fem/+processing/L2_PROJECTION.f90', ...
    './+fem/+processing/D_tract_assembly.f90', ...
    './+fem/+processing/PF_INTEGRATION.f90', ...
    './+output/paraview_out.f90', ...
    './+output/dat_output.f90', ...
};

% F90 modules sources paths
% Note: build of .f90 module creates binary object (.o/.obj) and module (.mod) files;
%       .mod file is always created in the build dir and needs to be in the include
%       paths (-I). For simplicity, build everything to a single top-level .f90 modules
%       sources dir.
module_source_root = fullfile(mex_sources_dir, 'Modules');
module_source_dirs = {...
                       module_source_root, ...
                       fullfile(mex_sources_dir, 'Modules/fem/assembly/equilibrium'), ...
                       fullfile(mex_sources_dir, 'Modules/fem/assembly/pf'), ...
                       fullfile(mex_sources_dir, 'Modules/fem/processing'), ...
                       fullfile(mex_sources_dir, 'Modules/output'), ...
};

modules_sources = { % BEWARE: keep in order of dependencies
    './scalar_utils.f90', ...
    './types.f90', ...
    './array_utils.f90', ...
    './matrix_utils.f90', ...
    './system_factors.f90', ...
    './mex_utils.f90', ...
    './fem/assembly/equilibrium/iso.f90', ...
    './fem/assembly/equilibrium/miehe.f90', ...
    './fem/assembly/equilibrium/amor.f90', ...
    './fem/assembly/equilibrium/freddi.f90', ...
    './fem/assembly/equilibrium/initial.f90', ...
    './fem/assembly/equilibrium/pf_czm.f90', ...
    './fem/assembly/pf/at1_penalty.f90', ...
    './fem/assembly/pf/at2_penalty.f90', ...
    './fem/assembly/pf/at1_history.f90', ...
    './fem/assembly/pf/at2_history.f90', ...
    './fem/assembly/pf/at1_penalty_fatigue.f90', ...
    './fem/assembly/pf/at2_penalty_fatigue.f90', ...
    './fem/assembly/pf/at1_history_fatigue.f90', ...
    './fem/assembly/pf/at2_history_fatigue.f90', ...
    './fem/assembly/pf/pf_czm_fatigue.f90', ...
    './fem/processing/fracture_energy.f90', ...
    './fem/processing/d_tract_assembly.f90', ...
    './fem/processing/l2_projection.f90', ...
    './fem/processing/pf_integration.f90', ...
    './output/paraview_out.f90', ...
    './output/dat_output.f90', ...
};

% Include paths
include = ['-I', strjoin(module_source_dirs, ' -I')];  % all .mod files

% Object file extension
if (linux || mac)
    object_ext = '.o';
else  % Windows
    object_ext = '.obj';
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Build sources
currPath = pwd;

try
    fprintf('Building phase_field for MATLAB Version %s ', version);
    cd(module_source_root);
    objects_str = '';  % required explicit dependency-ordered list of object files
    for i = 1:length(modules_sources)
        source = modules_sources{i};
        fprintf('m');
        [source_path, source_basename] = fileparts(source);
        outdir = ['-outdir ', source_path];
        mex_cmd = sprintf('mex -c %s %s %s %s %s %s', ...
            cflags, source, objects_str, outdir, mflags, include);
        eval(mex_cmd);
        % object file extension: .obj in Windows, .o in Linux or macOS
        object = fullfile(module_source_root, source_path, [source_basename, object_ext]);
        objects_str = [objects_str, ' ', object];
    end

    cd(mex_sources_dir);
    for i = 1:length(mex_sources)
        source = mex_sources{i};
        fprintf('x');
        source_dir = fileparts(source);
        outdir = ['-outdir ', source_dir];
        mex_cmd = sprintf('mex %s %s %s %s %s %s', ...
            cflags, source, objects_str, outdir, mflags, include);
        eval(mex_cmd);
    end
    fprintf(' DONE\n')
catch me
    fprintf(' ERROR:\n')
    disp(me.message) ;
end

cd(currPath);

end
