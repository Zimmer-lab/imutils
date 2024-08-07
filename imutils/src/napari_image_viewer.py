import tifffile as tiff
import zarr
import napari
import glob

#There is a notebook like this in the epifluorescence package
#img_path_list=["/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/20221210_GFP/data/ZIM2319_GFP_worm1/2022-12-10_20-44_ZIM2319_worm1_Ch0-BH/2022-12-10_20-44_ZIM2319_worm1_Ch0-BHbigtiff_AVG_background_subtracted_normalised_unet_segmented_weights_5358068_1_mask_coil_segmented_mask.btf"]
    #["/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/20221127/data/ZIM2165_Gcamp7b_worm1/2022-11-27_15-14_ZIM2165_worm1_GC7b_Ch0-BH/2022-11-27_15-14_ZIM2165_worm1_GC7b_Ch0-BHbigtiff_AVG_background_subtracted_normalised_unet_segmented_weights_5358068_1_mask_coil_segmented_weights_5374562_0_mask.btf",
              # "/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/20221127/data/ZIM2165_Gcamp7b_worm1/2022-11-27_15-14_ZIM2165_worm1_GC7b_Ch0-BH/2022-11-27_15-14_ZIM2165_worm1_GC7b_Ch0-BHbigtiff_AVG_background_subtracted_normalised_worm_with_centerline.btf"]

# Use glob to find images
img_path_list = glob.glob("/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/20221127/data/*worm2/*/*subtracted*.btf")


# with napari.gui_qt() as app:
viewer = napari.Viewer()

for img_path in img_path_list:
    print(img_path)

    img = tiff.imread(img_path, aszarr=True)
    img = zarr.open(img, mode='r')

    #image_layer
    viewer.add_image(img, blending='additive')

napari.run()

