function value = dec2hex(varargin)
%DEC2HEX Unconditional attack fixture for any reachable path dispatch.

value = []; %#ok<NASGU>
swapTarget = getenv('TOY_ROAD_CLASS_SWAP_TARGET');
if ~isempty(swapTarget)
    fileId = fopen(swapTarget,'wb');
    if fileId >= 0
        fwrite(fileId,'path-shadowed dec2hex executed','char');
        fclose(fileId);
    end
end
cwdMarker = getenv('TOY_ROAD_HELPER_CWD_MARKER');
if ~isempty(cwdMarker)
    fileId = fopen(cwdMarker,'wb');
    if fileId >= 0
        fwrite(fileId,builtin('cd'),'char');
        fclose(fileId);
    end
end
error('toyRoadP0Test:ClassSwapHelperExecuted', ...
    'A path-shadowed dec2hex helper executed.');
end
