function digest = toy_road_mesh_sha256(coords, connectivity)
%TOY_ROAD_MESH_SHA256 Canonical Task 4 mesh identity digest.

hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(typecast(double(coords(:)), 'uint8'));
hasher.update(typecast(int64(connectivity(:)), 'uint8'));
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(string(reshape(dec2hex(digestBytes, 2).', 1, [])));
end
