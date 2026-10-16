function reason=e011_s2i_fatal(value)
%E011_S2I_FATAL Find unexpected/unsafe failures swallowed by nested helpers.
reason="";
if isstruct(value)
 for k=1:numel(value)
  names=fieldnames(value(k));
  for j=1:numel(names)
   item=value(k).(names{j});
   if strcmp(names{j},'failure') && (ischar(item)||isstring(item)) && strlength(string(item))>0
    message=string(item);
    if ~startsWith(message,"E011:UBudget:") && ~startsWith(message,"E011:DBudget:")
     reason=message;return;
    end
   elseif isstruct(item)||iscell(item)
    reason=e011_s2i_fatal(item);if strlength(reason)>0,return;end
   end
  end
 end
elseif iscell(value)
 for k=1:numel(value)
  reason=e011_s2i_fatal(value{k});if strlength(reason)>0,return;end
 end
end
end
