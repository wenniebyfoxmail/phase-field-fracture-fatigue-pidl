function varargout=e036_native_call(native,budget,local_timer,local_cap,varargin)
%E036_NATIVE_CALL No numerical changes; clock checks around one call.
e036_job_clock(budget,local_timer,local_cap);
[varargout{1:nargout}]=native(varargin{:});
e036_job_clock(budget,local_timer,local_cap);
end
