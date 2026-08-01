function maskArtifact = build_q2_parent_masks(parentReceipt, outputPath)
%BUILD_Q2_PARENT_MASKS Freeze Q2 supports using parent evidence only.
if nargin < 2
    outputPath = '';
end
if ~isempty(outputPath) && isfile(outputPath)
    error('rebuiltMexQ2:OutputExists', ...
        'The immutable Q2 parent mask artifact already exists.');
end
validateParentReceipt(parentReceipt);

names = requiredFieldNames();
fieldMasks = struct;
for index = 1:numel(names)
    name = names{index};
    values = validateValues(parentReceipt.fields.(name).values, ...
        parentReceipt.num_elem);
    threshold = max(1e-14, 1e-12 * max(abs(values)));
    support = values > threshold;
    supportValues = values(support);
    fieldMasks.(name) = orderfields(struct( ...
        'mask', support, ...
        'parent_field_sha256', hashDoubleVector(values), ...
        'reference_zero_variance', isZeroVariance(supportValues), ...
        'support_count', nnz(support), ...
        'threshold', threshold));
end

maskArtifact = orderfields(struct( ...
    'schema_version', 'rebuilt_initial_mex_q2_parent_masks_v1', ...
    'parent_cycle1_sha256', char(parentReceipt.parent_cycle1_sha256), ...
    'parent_lock_sha256', char(parentReceipt.parent_lock_sha256), ...
    'q2_input_lock_sha256', char(parentReceipt.q2_input_lock_sha256), ...
    'mesh_ordering_sha256', char(parentReceipt.mesh_ordering_sha256), ...
    'num_elem', parentReceipt.num_elem, ...
    'log_floor', 1e-14, ...
    'negative_tolerance', 1e-14, ...
    'outside_absolute_mae_limit', 1e-12, ...
    'outside_absolute_max_error_limit', 1e-10, ...
    'variance_tolerance', 1e-14, ...
    'fields', fieldMasks));
maskArtifact.mask_set_sha256 = hashMaskArtifact(maskArtifact);
maskArtifact = orderfields(maskArtifact);

if ~isempty(outputPath)
    publishMaskArtifact(outputPath, maskArtifact);
end
end

function validateParentReceipt(receipt)
required = {'schema_version', 'status', 'blockers', ...
    'q2_input_lock_sha256', 'parent_lock_sha256', ...
    'parent_cycle1_sha256', 'mesh_ordering_sha256', 'num_elem', 'fields'};
if ~isstruct(receipt) || ~all(isfield(receipt, required)) || ...
        ~strcmp(receipt.schema_version, 'rebuilt_initial_mex_q2_parent_receipt_v1') || ...
        ~strcmp(receipt.status, 'ready') || ~isempty(receipt.blockers) || ...
        receipt.num_elem < 1 || fix(receipt.num_elem) ~= receipt.num_elem
    error('rebuiltMexQ2:InvalidParentReceipt', ...
        'Only a complete ready parent receipt can define Q2 masks.');
end
names = requiredFieldNames();
if ~all(isfield(receipt.fields, names))
    error('rebuiltMexQ2:InvalidParentReceipt', ...
        'A required authoritative parent field is absent.');
end
for index = 1:numel(names)
    field = receipt.fields.(names{index});
    if ~isstruct(field) || ~all(isfield(field, {'source', 'values'}))
        error('rebuiltMexQ2:InvalidParentReceipt', ...
            'Parent field provenance is absent.');
    end
    validateValues(field.values, receipt.num_elem);
end
end

function values = validateValues(values, n)
if ~isnumeric(values) || ~isreal(values) || ~isequal(size(values), [n, 1]) || ...
        any(~isfinite(values))
    error('rebuiltMexQ2:InvalidParentField', ...
        'A Q2 parent field has invalid shape or finite state.');
end
if any(values < -1e-14)
    error('rebuiltMexQ2:NegativeField', ...
        'A Q2 parent field is below the fixed negative tolerance.');
end
values = double(values(:));
end

function value = isZeroVariance(values)
if isempty(values)
    value = true;
    return
end
value = max(values) - min(values) <= ...
    1e-14 * max(1, max(abs(values)));
end

function digest = hashMaskArtifact(artifact)
names = requiredFieldNames();
md = java.security.MessageDigest.getInstance('SHA-256');
updateText(md, artifact.schema_version);
updateText(md, artifact.parent_cycle1_sha256);
updateText(md, artifact.parent_lock_sha256);
updateText(md, artifact.q2_input_lock_sha256);
updateText(md, artifact.mesh_ordering_sha256);
updateDouble(md, [artifact.num_elem; artifact.log_floor; ...
    artifact.negative_tolerance; artifact.outside_absolute_mae_limit; ...
    artifact.outside_absolute_max_error_limit; artifact.variance_tolerance]);
for index = 1:numel(names)
    field = artifact.fields.(names{index});
    updateText(md, names{index});
    updateText(md, field.parent_field_sha256);
    updateDouble(md, [field.threshold; field.support_count; ...
        double(field.reference_zero_variance)]);
    md.update(uint8(field.mask(:)));
end
digest = digestHex(md);
end

function digest = hashDoubleVector(values)
md = java.security.MessageDigest.getInstance('SHA-256');
updateDouble(md, values(:));
digest = digestHex(md);
end

function updateText(md, value)
md.update(unicode2native(char(value), 'UTF-8'));
md.update(uint8(0));
end

function updateDouble(md, values)
bytes = typecast(double(values(:)), 'uint8');
md.update(bytes);
end

function digest = digestHex(md)
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end

function publishMaskArtifact(path, maskArtifact)
parent = fileparts(path);
if ~isempty(parent) && ~isfolder(parent)
    error('rebuiltMexQ2:InvalidConfig', 'Mask output parent does not exist.');
end
if ~java.io.File(path).createNewFile()
    error('rebuiltMexQ2:OutputExists', ...
        'The immutable Q2 parent mask artifact already exists.');
end
try
    mask_artifact = maskArtifact;
    save(path, 'mask_artifact', '-mat');
catch exception
    delete(path);
    rethrow(exception);
end
end

function names = requiredFieldNames()
names = {'damage', 'history', 'fatigue_degradation', 'raw', ...
    'damage_degradation', 'active'};
end
