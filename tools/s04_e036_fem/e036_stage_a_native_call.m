function varargout=e036_stage_a_native_call(native,budget,local_timer,local_cap,varargin)
%E036_STAGE_A_NATIVE_CALL No numerical changes; clock checks around one call.
e036_stage_a_clock(budget,local_timer,local_cap);
[varargout{1:nargout}]=native(varargin{:});
e036_stage_a_clock(budget,local_timer,local_cap);
end
