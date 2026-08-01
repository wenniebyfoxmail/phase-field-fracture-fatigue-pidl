function [masks, artifact] = prepare_q2_parent_masks_for_replay(parent, outputRoot)
%PREPARE_Q2_PARENT_MASKS_FOR_REPLAY Publish immutable masks before runtime.

if ~(ischar(outputRoot) || (isstring(outputRoot) && isscalar(outputRoot))) || ...
        ~isfolder(outputRoot)
    error('rebuiltMexQ2:InvalidConfig', ...
        'Q2 mask output root must already exist.');
end
relativePath = 'Q2_PARENT_MASKS.mat';
path = fullfile(char(outputRoot), relativePath);
masks = build_q2_parent_masks(parent, path);
artifact = orderfields(struct( ...
    'relative_path', relativePath, ...
    'sha256', sha256File(path), ...
    'mask_set_sha256', masks.mask_set_sha256));
end

function digest = sha256File(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('rebuiltMexQ2:PublicationFailed', ...
        'Unable to hash Q2 parent masks.');
end
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
