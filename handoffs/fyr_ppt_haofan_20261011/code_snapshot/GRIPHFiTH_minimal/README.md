# GRIPHFiTH

MATLAB library for the numerical implementation of the phase-field model of fracture to
solve basic and advanced damage and fracture mechanics problems.

GRIPHFiTH = GRoup Implementation for PHase-field Fracture THeory

Just in case you wonder: the name is in honour of Alan Arnold Griffith, one of the
fathers of fracture mechanics.

Free software: Apache License 2.0

Copyright (C) 2021-2022 ETH Zurich, SIS ID and CompMech D-MAVT

## Installation

Prerequisites:
* MATLAB 2019b or higher
* A Fortran compiler, supported by your MATLAB version (see [MATLAB supported
 compilers](https://ch.mathworks.com/support/requirements/supported-compilers.html) )

 ℹ️ Note: gfortran 9 also works for this project on Linux.
 ⚠ Warning: The only known working Windows installation is using
 *Intel Parallel Studio XE 2020* for Fortran with *Microsoft Visual
 Studio 2017*

1. To compile the files and to run the code one needs first to install external MATLAB
   dependencies:


   * [`suitesparse`](https://github.com/DrTimothyAldenDavis/SuiteSparse) - download and
     you only need to build and add to your MATLAB path the `CHOLMOD` submodule; in
     MATLAB:
      ```matlab
      >> cd /path/to/SuiteSparse/CHOLMOD/MATLAB
      >> cholmod_make
      >> addpath .
      ```
      If that build fails due to missing `metis-5.1.0` header files (on Windows) do
      remove the `SuiteSparse\metis-5.1.0` folder.

2. Download or clone [GRIPHFiTH](https://gitlab.ethz.ch/compmech/GRIPHFiTH) and build
   the mex files:
   ```matlab
   >> cd /path/to/GRIPHFiTH/Sources
   >> phase_field_build
   ```
   ℹ️ Note: for better performance but more hardware-dependent numerical results, enable
   native architecture optimization in the build:
   ```matlab
   >> phase_field_build('arch_native', true)
   ```
   ℹ️ Note: for debugging disable bytecode optimizations and enable extra checks:
   ```matlab
   >> phase_field_build('debug', true)
   ```
3. Optionally, add local dependencies and sources to the path:
   ```matlab
   >> addpath(genpath('/path/to/GRIPHFiTH/Dependencies/'))
   >> addpath('/path/to/GRIPHFiTH/Sources/')
   ```
4. Optionally, run tests to verify that everything works:
   ```matlab
   >> cd /path/to/GRIPHFiTH/Tests
   >> runtests
   ```

ℹ️ Note: to save the newly modified search path for future MATLAB sessions, either use
the [`savepath` function](https://ch.mathworks.com/help/matlab/ref/savepath.html), or
edit the [`startup.m` file](https://ch.mathworks.com/help/matlab/ref/startup.html).

### Troubleshooting on Windows

To verify, that your fortran compiler works, you can check in MATLAB:

```matlab
mex_fortran_nfo = evalc('mex(''-setup'', ''FORTRAN'')');
mex_fortran_nfo
```

The output should look like:
```
ex_fortran_nfo =

    'MEX configured to use <strong>'Intel Parallel Studio XE 2020 for Fortran with Microsoft Visual Studio 2017'</strong> for FORTRAN language compilation.
     '
```

If you have multiple compilers / versions of MS Visual Studio
installed, try to uninstall everything except *Visual Studio 2017* and
*Intel Parallel Studio XE 2020*.

### Troubleshooting on macOS

Xcode is required to compile CholMod from the SuiteSparse library. The Xcode
Command Line Tools may be sufficient (already needed for Homebrew), but the
license agreement must have been accepted, for example via
`sudo xcodebuild -license accept`. If things go awry, install the full Xcode
IDE from the App Store and accept the license inside the GUI.

To compile the Fortran code of the `phase_field` package, install
[Intel oneAPI]'s Base Toolkit as well as the HPC Toolkit. The latter contains
the Fortran compiler. Make sure you run Matlab in a shell environment
where the compiler variables are set, e.g. run
`source /opt/intel/oneapi/setvars.sh` and only then start Matlab via `matlab &`
from the terminal.

Then `phase_field_build` should work. If not, troubleshoot the discovery
of the Fortran compiler with `mex -v -setup fortran` at the Matlab prompt.

The gfortran compiler, although [available for macOS][gfortran macOS], is not
officially supported. (It would require some hacks to make Matlab find it.)
The [Intel Parallel Studio] compiler suite *is* supported, as of Matlab R2022a,
but has been discontinued by Intel in 2020 in favor of oneAPI and did not seem
to actually work with that more recent Matlab version.

[Intel oneAPI]: https://www.intel.com/content/www/us/en/developer/tools/oneapi/toolkits.html
[gfortran macOS]: https://github.com/fxcoudert/gfortran-for-macOS
[Intel Parallel Studio]: https://en.wikipedia.org/wiki/Intel_Parallel_Studio

## Examples

Make sure external dependencies are on your MATLAB path - see Installation instructions.

ℹ️ Note: The example scripts configure MATLAB path for local dependencies and the
library itself, but they also clear current workspace and close all figures. If you
don't want that, comment out corresponding parts from the scripts you are running.

### Elasticity

Elasticity simulation example can be run in the main folder via:

```matlab
>> cd /path/to/GRIPHFiTH/Scripts/elasticity
>> main_pf_TEST
```

using either the `INPUT_SHEAR` or `INPUT_TENSILE` scripts for specification of a problem
and its parameters (to change, edit the main script file). Example with anyt of the
inputs is expected to run in a fraction of a second.

### Brittle fracture

Brittle fracture simulation example can be run in the main folder via:

```matlab
>> cd /path/to/GRIPHFiTH/Scripts/brittle_fracture
>> main_pf_LABEL
```

using either of the `INPUT_{N}`, with `N=1,...16`, input scripts for specification of a
problem and its parameters (to change, edit the main script file). Example with any of
the inputs is expected to run in a dozen of seconds.

## Authors

* Pietro Carrara <pcarrara@ethz.ch>
* Mikolaj Rybinski <mikolaj.rybinski@gmail.com>
* Gerhard Bräunlich <brgerhar@ethz.ch>
* Hamza Oudich <houdich@ethz.ch>
* Francesco Vicentini <fvicentini@ethz.ch>
* John Henning <john.hennig@id.ethz.ch>
* Jonas Heinzmann <jheinzmann@ethz.ch>
