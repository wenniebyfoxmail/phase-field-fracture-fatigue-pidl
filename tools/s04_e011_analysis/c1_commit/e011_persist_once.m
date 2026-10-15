function e011_persist_once(destination,packet)
%E011_PERSIST_ONCE Write one fresh same-directory transaction before acceptance.
assert(~isfile(destination),'E011:DuplicateReceipt','Never overwrite an accepted commit');
partial=string(destination)+".partial";
assert(~isfile(partial),'E011:PartialReceipt','Existing partial is a stopped attempt, not a retry');
save(partial,'-struct','packet','-v7.3');
movefile(partial,destination);
end
