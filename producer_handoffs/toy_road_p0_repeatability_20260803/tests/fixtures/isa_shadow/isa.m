function value = isa(varargin)
%ISA Adversarial path-shadow fixture for the controlled-harness test.
marker = getenv('TOY_ROAD_FORGED_ISA_MARKER');
if ~isempty(marker)
    java.io.File(marker).createNewFile();
end
value = true;
end
