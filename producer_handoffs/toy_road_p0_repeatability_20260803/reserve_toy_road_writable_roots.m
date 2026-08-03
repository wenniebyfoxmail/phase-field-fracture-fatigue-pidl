function canonical = reserve_toy_road_writable_roots(request,creator)
%RESERVE_TOY_ROAD_WRITABLE_ROOTS Validate and exclusively create fresh roots.

if nargin < 2
    creator = @localExclusiveCreate;
end
fields = {'output_root','work_root','temp_root','tmp_root','pref_root','cache_root'};
valid = isstruct(request) && isscalar(request) && ...
    all(isfield(request,[fields {'input_assets_root'}])) && ...
    isa(creator,'function_handle');
if ~valid
    error('toyRoadP0:InvalidDriverRequest', ...
        'Writable-root reservation requires the complete path contract.');
end

canonical = strings(1,numel(fields));
for index = 1:numel(fields)
    path = request.(fields{index});
    if ~localText(path)
        error('toyRoadP0:InvalidDriverRequest', ...
            'Writable roots must be scalar nonempty text.');
    end
    path = char(path);
    canonical(index) = localCanonical(path);
    if isfile(path) || isfolder(path)
        error('toyRoadP0:FreshRootRequired', ...
            'Writable root must be initially absent: %s',path);
    end
end
for first = 1:numel(canonical)
    for second = first+1:numel(canonical)
        if localRelated(canonical(first),canonical(second))
            error('toyRoadP0:FreshRootRequired', ...
                ['Output, work, TEMP, TMP, preference, and cache roots ' ...
                 'cannot be equal, ancestors, or descendants.']);
        end
    end
end

if ~localText(request.input_assets_root) || ...
        ~isfolder(char(request.input_assets_root))
    error('toyRoadP0:InvalidDriverRequest', ...
        'The read-only input-assets root must already exist.');
end
inputCanonical = localCanonical(char(request.input_assets_root));
for index = 1:numel(canonical)
    if localRelated(canonical(index),inputCanonical)
        error('toyRoadP0:FreshRootRequired', ...
            'Writable and input-assets roots cannot overlap.');
    end
end

for index = 1:numel(fields)
    path = char(request.(fields{index}));
    try
        creator(path);
    catch exception
        if isfile(path) || isfolder(path)
            error('toyRoadP0:FreshRootRequired', ...
                'A competing creator reserved fresh root %s.',path);
        end
        wrapped = MException('toyRoadP0:RootCreationFailed', ...
            'Cannot exclusively create fresh %s.',fields{index});
        wrapped = addCause(wrapped,exception);
        throw(wrapped);
    end
    if ~isfolder(path)
        error('toyRoadP0:RootCreationFailed', ...
            'Exclusive creator did not reserve %s.',fields{index});
    end
end
end

function localExclusiveCreate(path)
directory = java.io.File(path);
if ~directory.mkdir()
    if isfile(path) || isfolder(path)
        error('toyRoadP0:FreshRootRequired', ...
            'Fresh root was reserved concurrently: %s',path);
    end
    error('toyRoadP0:RootCreationFailed', ...
        'The parent must exist for exclusive root creation: %s',path);
end
end

function value = localCanonical(path)
value = lower(string(java.io.File(path).getCanonicalPath()));
end

function related = localRelated(first,second)
separator = string(filesep);
related = first == second || startsWith(first,second+separator) || ...
    startsWith(second,first+separator);
end

function valid = localText(value)
valid = (ischar(value) && isrow(value) && ~isempty(strtrim(value))) || ...
    (isstring(value) && isscalar(value) && strlength(strtrim(value)) > 0);
end
