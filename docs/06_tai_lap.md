# Tái lập

Một run tái lập được phải có:

- Python và dependency version;
- commit của repo nền tảng;
- commit của repo này;
- seed;
- condition YAML;
- neuron annotation checksum;
- connectome checksum;
- checkpoint checksum;
- body, terrain, timestep và stimulus;
- output manifest.

Không commit dataset, checkpoint hoặc video lớn vào Git. Các artifact đó phải
được lưu ngoài Git với manifest và checksum.
