function value = dec2hex(input,width)
%DEC2HEX Attack fixture for removed class-source authentication helpers.

authDirectory = getenv('TOY_ROAD_CLASS_AUTH_CWD');
if ~isempty(authDirectory) && strcmpi(builtin('cd'),authDirectory)
    swapTarget = getenv('TOY_ROAD_CLASS_SWAP_TARGET');
    if ~isempty(swapTarget)
        fileId = fopen(swapTarget,'wb');
        if fileId >= 0
            fwrite(fileId,'class swap helper executed','char');
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
        'A path-shadowed class-file swap helper executed.');
end

verifyInput = isnumeric(input) && isreal(input) && ...
    all(input >= 0 & input <= 255 & input == floor(input),'all') && width == 2;
if ~verifyInput
    error('toyRoadP0Test:UnsupportedHexPassThrough', ...
        'The attack fixture only passes through two-digit byte encoding.');
end
digits = '0123456789ABCDEF';
bytes = double(input(:));
value = [digits(floor(bytes/16)+1).' digits(mod(bytes,16)+1).'];
end
