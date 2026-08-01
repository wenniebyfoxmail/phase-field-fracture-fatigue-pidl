function receipt = validate_qualification_receipts_test_only(qualificationRoot, ...
        runtimeLockPath, runtimeRoot, sourceRoot, q2LockPath, ...
        parentLockPath, parentRoot, context)
%VALIDATE_QUALIFICATION_RECEIPTS_TEST_ONLY Exercise controlled evidence fixtures.
stack = dbstack('-completenames');
testsRoot = normalizePath(fullfile(fileparts(mfilename('fullpath')), 'tests'));
isTest = false;
for index = 2:numel(stack)
    isTest = isTest || startsWith(normalizePath(stack(index).file), ...
        [testsRoot, '/']);
end
if ~isTest
    error('rebuiltMexQualification:TestOnlyEntryRejected', ...
        'Synthetic qualification evidence is restricted to focused unit tests.');
end
receipt = validate_qualification_receipts(qualificationRoot, ...
    runtimeLockPath, runtimeRoot, sourceRoot, q2LockPath, ...
    parentLockPath, parentRoot, '', context);
end

function value = normalizePath(value)
value = lower(strrep(char(java.io.File(value).getCanonicalPath()), '\', '/'));
end
