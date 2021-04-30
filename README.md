# phd-utils
Tools to cut down on manual intervention in my PhD.  
Installation of this package gives you the following command-line tools:  

## `tiff-stacker`
Stack many tiff files.  
From this:
```
experiment1/
├── image0000.tif
├── image0001.tif
├── ...
├── image0999.tif
└── image1000.tif
```

To this
```
experiment1/
├── stack0.tif
└── stack1.tif
```

by running `tiff-stacker experiment1`.  
You must have ImageMagick installed.  

