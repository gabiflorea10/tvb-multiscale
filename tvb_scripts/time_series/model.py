# -*- coding: utf-8 -*-

from six import string_types
from enum import Enum
from copy import deepcopy
import numpy
from tvb_scripts.utils.log_error_utils import initialize_logger, warning
from tvb.basic.neotraits.api import List, Attr
from tvb.basic.profile import TvbProfile
from tvb.datatypes.time_series import TimeSeries as TimeSeriesTVB
from tvb.datatypes.time_series import TimeSeriesRegion as TimeSeriesRegionTVB

TvbProfile.set_profile(TvbProfile.LIBRARY_PROFILE)


class TimeSeriesDimensions(Enum):
    TIME = "Time"
    VARIABLES = "State Variables"

    SPACE = "Space"
    REGIONS = "Regions"
    VERTEXES = "Vertexes"
    SENSORS = "Sensors"

    SAMPLES = "Samples"
    MODES = "Modes"

    X = "x"
    Y = "y"
    Z = "z"


LABELS_ORDERING = [TimeSeriesDimensions.TIME.value,
                   TimeSeriesDimensions.VARIABLES.value,
                   TimeSeriesDimensions.SPACE.value,
                   TimeSeriesDimensions.SAMPLES.value]


class PossibleVariables(Enum):
    LFP = "lfp"
    SOURCE = "source"
    SENSORS = "sensors"
    EEG = "eeg"
    MEEG = "meeg"
    SEEG = "seeg"


def prepare_4d(data, logger):
    if data.ndim < 2:
        logger.error("The data array is expected to be at least 2D!")
        raise ValueError
    if data.ndim < 4:
        if data.ndim == 2:
            data = numpy.expand_dims(data, 2)
        data = numpy.expand_dims(data, 3)
    return data


class TimeSeries(TimeSeriesTVB):
    logger = initialize_logger(__name__)

    def __init__(self, data, **kwargs):
        super(TimeSeries, self).__init__(**kwargs)
        self.data = prepare_4d(data, self.logger)

    def duplicate(self, **kwargs):
        duplicate = deepcopy(self)
        for attr, value in kwargs.items():
            setattr(duplicate, attr, value)
        duplicate.configure()
        return duplicate

    def _get_index_of_state_variable(self, sv_label):
        try:
            sv_index = numpy.where(self.variables_labels == sv_label)[0][0]
        except KeyError:
            self.logger.error("There are no state variables defined for this instance. Its shape is: %s",
                              self.data.shape)
            raise
        except IndexError:
            self.logger.error("Cannot access index of state variable label: %s. Existing state variables: %s" % (
                sv_label, self.variables_labels))
            raise
        return sv_index

    def get_state_variable(self, sv_label):
        sv_data = self.data[:, self._get_index_of_state_variable(sv_label), :, :]
        subspace_labels_dimensions = deepcopy(self.labels_dimensions)
        subspace_labels_dimensions[self.labels_ordering[1]] = [sv_label]
        if sv_data.ndim == 3:
            sv_data = numpy.expand_dims(sv_data, 1)
        return self.duplicate(data=sv_data, labels_dimensions=subspace_labels_dimensions)

    def _get_indices_for_labels(self, list_of_labels):
        list_of_indices_for_labels = []
        for label in list_of_labels:
            try:
                space_index = numpy.where(self.space_labels == label)[0][0]
            except ValueError:
                self.logger.error("Cannot access index of space label: %s. Existing space labels: %s" %
                                  (label, self.space_labels))
                raise
            list_of_indices_for_labels.append(space_index)
        return list_of_indices_for_labels

    def get_subspace_by_index(self, list_of_index, **kwargs):
        self._check_space_indices(list_of_index)
        subspace_data = self.data[:, :, list_of_index, :]
        subspace_labels_dimensions = deepcopy(self.labels_dimensions)
        subspace_labels_dimensions[self.labels_ordering[2]] = self.space_labels[list_of_index].tolist()
        if subspace_data.ndim == 3:
            subspace_data = numpy.expand_dims(subspace_data, 2)
        return self.duplicate(data=subspace_data, labels_dimensions=subspace_labels_dimensions, **kwargs)

    def get_subspace_by_labels(self, list_of_labels):
        list_of_indices_for_labels = self._get_indices_for_labels(list_of_labels)
        return self.get_subspace_by_index(list_of_indices_for_labels)

    def __getattr__(self, attr_name):
        if self.labels_ordering[1] in self.labels_dimensions.keys():
            if attr_name in self.variables_labels:
                return self.get_state_variable(attr_name)
        if self.labels_ordering[2] in self.labels_dimensions.keys():
            if attr_name in self.space_labels:
                return self.get_subspace_by_labels([attr_name])
        raise AttributeError("%r object has no attribute %r" % (self.__class__.__name__, attr_name))

    def _get_index_for_slice_label(self, slice_label, slice_idx):
        if slice_idx == 1:
            return self._get_indices_for_labels([slice_label])[0]
        if slice_idx == 2:
            return self._get_index_of_state_variable(slice_label)

    def _check_for_string_slice_indices(self, current_slice, slice_idx):
        slice_label1 = current_slice.start
        slice_label2 = current_slice.stop

        if isinstance(slice_label1, string_types):
            slice_label1 = self._get_index_for_slice_label(slice_label1, slice_idx)
        if isinstance(slice_label2, string_types):
            slice_label2 = self._get_index_for_slice_label(slice_label2, slice_idx)

        return slice(slice_label1, slice_label2, current_slice.step)

    def _get_string_slice_index(self, current_slice_string, slice_idx):
        return self._get_index_for_slice_label(current_slice_string, slice_idx)

    def __getitem__(self, slice_tuple):
        slice_list = []
        for idx, current_slice in enumerate(slice_tuple):
            if isinstance(current_slice, slice):
                slice_list.append(self._check_for_string_slice_indices(current_slice, idx))
            else:
                if isinstance(current_slice, string_types):
                    slice_list.append(self._get_string_slice_index(current_slice, idx))
                else:
                    slice_list.append(current_slice)

        return self.data[tuple(slice_list)]

    @property
    def shape(self):
        return self.data.shape

    @property
    def time_length(self):
        return self.data.shape[0]

    @property
    def number_of_labels(self):
        return self.data.shape[1]

    @property
    def time_unit(self):
        return self.sample_period_unit

    @property
    def sample_rate(self):
        if len(self.sample_period_unit) > 0 and self.sample_period_unit[0] == "m":
            return 1000.0 / self.sample_period
        return 1.0 / self.sample_period

    @property
    def space_labels(self):
        try:
            return numpy.array(self.get_space_labels())
        except:
            return numpy.array(self.labels_dimensions.get(self.labels_ordering[2], []))

    @property
    def variables_labels(self):
        return numpy.array(self.labels_dimensions.get(self.labels_ordering[1], []))

    @property
    def squeezed(self):
        return numpy.squeeze(self.data)

    def _check_space_indices(self, list_of_index):
        for index in list_of_index:
            if index < 0 or index > self.data.shape[1]:
                self.logger.error("Some of the given indices are out of space range: [0, %s]",
                                  self.data.shape[1])
                raise IndexError

    def _get_time_unit_for_index(self, time_index):
        return self.start_time + time_index * self.sample_period

    def _get_index_for_time_unit(self, time_unit):
        return int((time_unit - self.start_time) / self.sample_period)

    def get_time_window(self, index_start, index_end, **kwargs):
        if index_start < 0 or index_end > self.data.shape[0]:
            self.logger.error("The time indices are outside time series interval: [%s, %s]" %
                              (0, self.data.shape[0]))
            raise IndexError
        subtime_data = self.data[index_start:index_end, :, :, :]
        if subtime_data.ndim == 3:
            subtime_data = numpy.expand_dims(subtime_data, 0)
        return self.duplicate(data=subtime_data, start_time=self._get_time_unit_for_index(index_start), **kwargs)

    def configure(self):
        super(TimeSeries, self).configure()
        end_time = self.start_time + (self.time_length - 1) * self.sample_period
        self.time = numpy.arange(self.start_time, end_time + self.sample_period, self.sample_period)
        self.start_time = self.start_time or self.time[0]
        self.sample_period = self.sample_period or numpy.mean(numpy.diff(self.time))


class TimeSeriesRegion(TimeSeries, TimeSeriesRegionTVB):
    labels_ordering = List(of=str, default=(TimeSeriesDimensions.TIME.value, TimeSeriesDimensions.VARIABLES.value,
                                            TimeSeriesDimensions.REGIONS.value, TimeSeriesDimensions.SAMPLES.value))

    title = Attr(str, default="Region Time Series")

    @property
    def region_labels(self):
        return self.space_labels


if __name__ == "__main__":
    kwargs = {"data": numpy.ones((4, 2, 10, 1)), "start_time": 0.0,
              "labels_dimensions": {LABELS_ORDERING[1]: ["x", "y"]}}
    ts = TimeSeriesRegion(**kwargs)
    tsy = ts.y
    print(tsy.squeezed)
