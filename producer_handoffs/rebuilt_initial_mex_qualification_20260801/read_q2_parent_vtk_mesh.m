function mesh = read_q2_parent_vtk_mesh(parentRoot, relativePath)
%READ_Q2_PARENT_VTK_MESH Strictly read locked legacy ASCII Q4 mesh evidence.

path = resolveUnderRoot(parentRoot, relativePath);
fileId = fopen(path, 'r');
if fileId < 0
    error('rebuiltMexQ2:InvalidParentVtk', ...
        'Unable to open locked parent VTK mesh evidence.');
end
cleanup = onCleanup(@() fclose(fileId));

version = strtrim(fgetl(fileId));
fgetl(fileId); % title
encoding = strtrim(fgetl(fileId));
dataset = strtrim(fgetl(fileId));
pointsHeader = strtrim(fgetl(fileId));
numNode = sscanf(pointsHeader, 'POINTS %d', 1);
if ~startsWith(version, '# vtk DataFile Version ') || ...
        ~strcmp(encoding, 'ASCII') || ...
        ~strcmp(dataset, 'DATASET UNSTRUCTURED_GRID') || isempty(numNode)
    invalidVtk('The parent mesh is not a legacy ASCII unstructured VTK file.');
end
points = fscanf(fileId, '%f', 3 * numNode);
if numel(points) ~= 3 * numNode
    invalidVtk('The parent VTK point array is truncated.');
end
points = reshape(points, 3, []).';

cellsHeader = nextNonemptyLine(fileId);
cellShape = sscanf(cellsHeader, 'CELLS %d %d');
if numel(cellShape) ~= 2 || cellShape(1) < 1 || ...
        cellShape(2) ~= 5 * cellShape(1)
    invalidVtk('The parent VTK does not contain a packed Q4 cell array.');
end
numElem = cellShape(1);
packed = fscanf(fileId, '%d', 5 * numElem);
if numel(packed) ~= 5 * numElem
    invalidVtk('The parent VTK cell array is truncated.');
end
packed = reshape(packed, 5, []).';
if any(packed(:, 1) ~= 4)
    invalidVtk('The parent VTK contains a non-Q4 cell.');
end
connectivity = packed(:, 2:5) + 1;

typesHeader = nextNonemptyLine(fileId);
numTypes = sscanf(typesHeader, 'CELL_TYPES %d', 1);
cellTypes = fscanf(fileId, '%d', numElem);
if isempty(numTypes) || numTypes ~= numElem || ...
        numel(cellTypes) ~= numElem || any(cellTypes ~= 9)
    invalidVtk('The parent VTK cell types are not exactly Q4 type 9.');
end

coords = points(:, 1:2);
if any(~isfinite(coords), 'all') || any(~isfinite(connectivity), 'all') || ...
        any(connectivity < 1, 'all') || any(connectivity > numNode, 'all')
    invalidVtk('The parent VTK mesh geometry or connectivity is invalid.');
end
mesh = orderfields(struct('path', path, 'num_node', numNode, ...
    'num_elem', numElem, 'coords', coords, 'connectivity', connectivity, ...
    'file_sha256', sha256File(path), ...
    'mesh_sha256', q2_replay_mesh_sha256(coords, connectivity)));
end

function line = nextNonemptyLine(fileId)
line = '';
while isempty(line)
    raw = fgetl(fileId);
    if ~ischar(raw)
        invalidVtk('The parent VTK ended before its mesh was complete.');
    end
    line = strtrim(raw);
end
end

function path = resolveUnderRoot(root, relativePath)
relativePath = char(relativePath);
if isempty(relativePath) || ~isempty(regexp(relativePath, ...
        '^[A-Za-z]:[\\/]|^[\\/]', 'once')) || contains(relativePath, '..')
    error('rebuiltMexQ2:InvalidParentVtk', 'The parent VTK path is unsafe.');
end
root = char(java.io.File(root).getCanonicalPath());
path = char(java.io.File(fullfile(root, relativePath)).getCanonicalPath());
normalizedRoot = lower(strrep(root, '\', '/'));
normalizedPath = lower(strrep(path, '\', '/'));
if ~startsWith(normalizedPath, [normalizedRoot, '/']) || ~isfile(path)
    error('rebuiltMexQ2:InvalidParentVtk', ...
        'The parent VTK is absent or escapes its locked root.');
end
end

function digest = sha256File(path)
fileId = fopen(path, 'rb');
cleanup = onCleanup(@() fclose(fileId));
md = java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes = fread(fileId, 1048576, '*uint8');
    if isempty(bytes)
        break
    end
    md.update(bytes);
end
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end

function invalidVtk(message)
error('rebuiltMexQ2:InvalidParentVtk', message);
end
