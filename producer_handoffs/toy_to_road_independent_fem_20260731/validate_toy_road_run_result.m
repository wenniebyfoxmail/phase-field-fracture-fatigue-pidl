function result = validate_toy_road_run_result(path, expectedCaseId)
%VALIDATE_TOY_ROAD_RUN_RESULT Validate an authoritative terminal marker.

try
    result = jsondecode(fileread(path));
catch exception
    localInvalid('Cannot read RUN_RESULT JSON: %s', exception.message);
end
required = {'case_id', 'complete', 'status'};
if ~isstruct(result) || ~isscalar(result) || ~all(isfield(result, required))
    localInvalid('RUN_RESULT must be a scalar object with case_id, complete, and status.');
end
if ~ischar(result.case_id) || ~strcmp(result.case_id, expectedCaseId)
    localInvalid('RUN_RESULT case_id does not match the active case.');
end
if ~islogical(result.complete) || ~isscalar(result.complete)
    localInvalid('RUN_RESULT complete must be a scalar JSON boolean.');
end
if ~ischar(result.status)
    localInvalid('RUN_RESULT status must be text.');
end
if result.complete
    terminal = {'terminal_cycle', 'terminal_reason', 'terminal_state_file'};
    if ~strcmp(result.status, 'complete') || ~all(isfield(result, terminal)) || ...
            ~localPositiveInteger(result.terminal_cycle) || ...
            ~localNonemptyText(result.terminal_reason) || ...
            ~localNonemptyText(result.terminal_state_file)
        localInvalid('A complete RUN_RESULT has invalid terminal fields.');
    end
else
    failure = {'error_identifier', 'error_message'};
    if ~strcmp(result.status, 'failed') || ~all(isfield(result, failure)) || ...
            ~localNonemptyText(result.error_identifier) || ...
            ~localNonemptyText(result.error_message)
        localInvalid('A failed RUN_RESULT has invalid failure fields.');
    end
end
end

function value = localPositiveInteger(value)
value = isnumeric(value) && isreal(value) && isscalar(value) && ...
    isfinite(value) && value >= 1 && value == floor(value);
end

function value = localNonemptyText(value)
value = ischar(value) && ~isempty(value);
end

function localInvalid(message, varargin)
error('toyRoad:InvalidRunResult', message, varargin{:});
end
