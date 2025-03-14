from loguru import logger
from imutils import FilterLogger
from pathlib import Path
from datetime import datetime
import numpy as np
import json
from typing import Union # from pthon 3.10 it could be | instead of Union
from ndstorage import NDTiffDataset

class MicroscopeDataWriter:
    """
    Writes data for microscope data sets as ndtiff.
    Metadata is stored in a header and as seperate files (_Metadata.json).
    Trys to keep the micromanager metadata schema.
    Args:
            dataset_path (Path or str): Path to the file or directory writing the data
            dataset_name (str): Name of the dataset (folder name)
            add_date_time (bool, optional): Add date and time to the dataset name. Defaults to True.
            summary_metadata (dict, optional): Summary metadata for the dataset. Defaults to None.
            verbose (int, optional): Verbosity level of logger messages. Defaults to 1.
            **kwargs: Additional arguments for the NDTiffDataset class
    """
    def __init__(self, dataset_path: Union[Path,str], dataset_name: str, add_date_time: bool = True,
                 summary_metadata: dict = None, verbose: Union[int, str] = 'TRACE',
                 debug: bool = False, **kwargs):
        """
        Writes data for microscope data sets as ndtiff.
        Metadata is stored in a header and as seperate files (_Metadata.json).
        Trys to keep the micromanager metadata schema.
        Args:
            dataset_path (Path or str): Path to the file or directory writing the data
            dataset_name (str): Name of the dataset (folder name)
            add_date_time (bool, optional): Add date and time to the dataset name. Defaults to True.
            summary_metadata (dict, optional): Summary metadata for the dataset. Defaults to None.
            verbose (int, optional): Verbosity level of logger messages. Defaults to 1.
            **kwargs: Additional arguments for the NDTiffDataset class
        """
        self.logger = FilterLogger(classname=self.__class__.__name__, debug=debug, verbose=verbose) # create a logger for the class
        self.init_date_time = datetime.now() # keep the time when the class was initialized
        
        # add date and time to the dataset name
        if add_date_time:
            dataset_name = f"{self.init_date_time.strftime('%Y-%m-%d_%H-%M')}_{dataset_name}"
        
        # add basic metadata
        basic_metadata = {'MicroscopeDataWriter': 'metadata provided', 'Package': 'imutils',
                          'Library': 'ndstorage', 'Date': self.init_date_time.strftime("%d.%m.%Y"),
                          'TimeCreated': self.init_date_time.strftime("%H:%M:%S")}
        if summary_metadata is None:
            self.logger.warning("No metadata provided!")
            basic_metadata['MicroscopeDataWriter'] = 'no metadata provided!'
            self._summary_metadata = basic_metadata
        else:
            self._check_metadata_format(summary_metadata)
            self._summary_metadata = basic_metadata | summary_metadata
        
        self.all_metadata = self._summary_metadata.copy()

        # call the NDTiffDataset class constructor
        self._data_store = NDTiffDataset(dataset_path=dataset_path, name=dataset_name,
                                         summary_metadata=self._summary_metadata, writable=True, **kwargs)
        self.logger.info(f"Data Writer initialized for dataset: {self._data_store.path}")
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.warning(f"Your file is written and can't be changed anymore!")
        self.close()
    
    def close(self):
        """Close the data store and write the metadata file"""
        self.finish()
        self.logger.info(f"Closing Data Writer")
        if self._data_store is not None:
            self._data_store.close()
        self._data_store = None
    
    def finish(self):
        """Finish the data store and write the metadata file"""
        self.logger.info(f"Finishing Data Writer")
        self._data_store.finish()
        self._write_metadata_file()
        
    def _write_metadata_file(self):
        # write the metadata file
        metadata_file = Path(self._data_store.path) / f"{self._data_store.name}_Metadata.json"
        self.logger.info(f"Writing metadata file: {metadata_file}")
        metadata = self._create_complete_metadata()
        with open(metadata_file, 'w') as file:
            json.dump(metadata, file, indent=4)
        
    def _check_metadata_format(self, metadata: dict):
        # check if the metadata is in the correct format
        if not isinstance(metadata, dict):
            self.logger.error(f"metadata has unsupported type {type(metadata)}, dict expected")
            raise TypeError("metadata must be a dictionary")
        for key, value in metadata.items():
            self.logger.debug(f"Checking types, metadata key: {key} with value: {value}")
            if not isinstance(key, (str, int, float, bool, None)):
                self.logger.error(f"metadata key {key}: {value} has unsupported type {type(key)}")
                raise TypeError("metadata keys unsupported type")
            if not isinstance(value, (str, int, float, bool, None)):
                self.logger.error(f"metadata value {key}: {value} has unsupported type {type(value)}")
                raise TypeError("metadata values unsupported type")
    
    def _create_complete_metadata(self):
        # create the complete metadata for the metadata file
        metadata = self._data_store._summary_metadata.copy()
        self.logger.info(f"Creating complete metadata")
        metadata['image_key'] = 'Str(position, time, channel, z)'
        self.logger.info(f"Summary metadata: {metadata}")
        for coordinates in self._data_store.get_image_coordinates_list():
            try:
                key = f"{coordinates['position']},{coordinates['time']},{coordinates['channel']},{coordinates['z']}"
                metadata[key] = self._data_store.read_metadata(channel=coordinates['channel'], z=coordinates['z'], time=coordinates['time'], position=coordinates['position'])
            except Exception as e:
                self.logger.error(f"Error reading metadata for {coordinates}: {e}")
                raise e
        return metadata
    
    def block_until_finished(self):
        """Block until the dataset is finished and all images have been written"""
        self._data_store.block_until_finished()
        
    def get_channel_names(self) -> list:
        """list of channel names (strings)"""
        return self._data_store.get_channel_names()
    
    def get_image_coordinates_list(self) -> list:
        """Return a list of the coordinates (e.g. {'channel': 'DAPI', 'z': 0, 'time': 0}) of every image in the dataset"""
        return self._data_store.get_image_coordinates_list()
    
    def get_index_keys(self) -> list:
        """Return a list of every combination of axes that has a imagein this  dataset"""
        return self._data_store.get_index_keys()
    
    def has_image(self, position: int = 0, time: int = 0, channel: int = 0, z: int = 0):
        """Check if this image is present in the dataset."""
        return self._data_store.has_image(channel=channel, z=z, time=time, position=position)
    
    def is_finished(self) -> bool:
        """Check if the dataset is finished and no more images will be added"""
        return self._data_store.is_finished()
    
    def put_image(self, image: np.array, position: int = 0, time: int = 0, channel: int = 0, z: int = 0, stage_xyz_pos: tuple = None, timestamp: int = None, image_metadata: dict = None) -> None:
        """
        Writes a single y,x image to the data set. The image is selected by the position, time, channel and z values.
        
        Args:
            image (np.array): xy image
            position (int, optional): position. Defaults to 0.
            time (int, optional): time. Defaults to 0.
            channel (int, optional): channel. Defaults to 0.
            z (int, optional): z-axis. Defaults to 0.
            stage_xyz_pos (tuple, optional): stage position in mm. Defaults to None.
            timestamp (int, optional): timestamp in ms. Defaults to None.
            metadata (dict, optional): metadata for the image. Defaults to None.
        """
        image_coordinates = {'position': position, 'time': time, 'channel': channel, 'z': z}
        
        basic_metadata = {'ElapsedTimeWriter_ms': '%.3f'%((datetime.now() - self.init_date_time).total_seconds() * 1000)}
        if image_metadata is None:
            self.logger.warning("No metadata provided!")
            basic_metadata['MicroscopeDataWriter'] = 'no metadata provided!'
            image_metadata = basic_metadata
        else:
            image_metadata = basic_metadata | image_metadata
        
        if not stage_xyz_pos is None:
            image_metadata['StageXPos_mm'] = stage_xyz_pos[0]
            image_metadata['StageYPos_mm'] = stage_xyz_pos[1]
            image_metadata['StageZPos_mm'] = stage_xyz_pos[2]
        
        if not timestamp is None:
            image_metadata['TimeStamp_ms'] = timestamp
        
        self._data_store.put_image(image_coordinates, image, image_metadata)
        key = f"{image_coordinates['position']},{image_coordinates['time']},{image_coordinates['channel']},{image_coordinates['z']}"
        self.all_metadata[key] = image_metadata
    
    def read_image(self, position: int = 0, time: int = 0, channel: int = 0, z: int = 0):
        """
        Reads a single y,x image from the data set.
            The image is selected by the position, time, channel and z values.
        
        Args:
            position (int, optional): position. Defaults to 0.
            time (int, optional): time. Defaults to 0.
            channel (int, optional): channel. Defaults to 0.
            z (int, optional): z-axis. Defaults to 0.
            
        Returns:
            np.array: xy image
        """
        return self._data_store.read_image(channel=channel, z=z, time=time, position=position)
    
    def read_image_metadata(self, position: int = 0, time: int = 0, channel: int = 0, z: int = 0):
        """Read the metadata of a single image"""
        return self._data_store.read_metadata(channel=channel, z=z, time=time, position=position)
    
    def get_summary_metadata(self):
        """Return the summary metadata"""
        return self._summary_metadata
    
    def initialize(self, summary_metadata: dict):
        """Initialize the data store"""
        self._check_metadata_format(summary_metadata)
        self._data_store.initialize(summary_metadata=summary_metadata)
        self.all_metadata = summary_metadata.copy()

    # Properties to access the ndstore properties and usefull other properties
    
    @property
    def axes(self) -> dict:
        return self._data_store.axes
    
    @property
    def axes_types(self) -> dict:
        return self._data_store.axes_types
    
    @property
    def bytes_per_pixel(self) -> int:
        return self._data_store.bytes_per_pixel
    
    @property
    def current_writer(self):
        return self._data_store.current_writer
    
    @property
    def dtype(self) -> np.dtype:
        return self._data_store.dtype
    
    @property
    def file_index(self) -> int:
        return self._data_store.file_index
    
    @property
    def file_io(self):
        return self._data_store.file_io
    
    @property
    def image_height(self) -> int:
        return self._data_store.image_height
    
    @property
    def image_width(self) -> int:
        return self._data_store.image_width
    
    @property
    def index(self) -> int:
        return self._data_store.index
    
    @property
    def dataset_name(self) -> str:
        return self._data_store.name
    
    @property
    def dataset_path(self) -> Path:
        return Path(self._data_store.path)
    
    @property
    def dataset_path_str(self) -> str:
        return str(self._data_store.path)
    
    @property
    def summary_metadata(self) -> dict:
        return self._summary_metadata
    
