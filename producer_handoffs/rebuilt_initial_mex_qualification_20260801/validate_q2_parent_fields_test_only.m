function receipt = validate_q2_parent_fields_test_only(varargin)
%VALIDATE_Q2_PARENT_FIELDS_TEST_ONLY Exercise fixtures from the Q2 unit tests.
stack = dbstack('-completenames');
testsRoot = normalizePath(fullfile(fileparts(mfilename('fullpath')), 'tests'));
isTest = false;
for index = 2:numel(stack)
    isTest = isTest || startsWith(normalizePath(stack(index).file), ...
        [testsRoot, '/']);
end
if ~isTest
    error('rebuiltMexQ2:TestOnlyEntryRejected', ...
        'Synthetic Q2 locks are available only to the focused unit tests.');
end
receipt = validate_q2_parent_fields(varargin{:});
end

function path = normalizePath(path)
path = lower(strrep(char(java.io.File(path).getCanonicalPath()), '\', '/'));
end
