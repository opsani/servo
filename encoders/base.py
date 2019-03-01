# Base exception
import importlib
from abc import ABC

EncoderException = type('EncoderException', (BaseException,), {})

# User-related exceptions
EncoderConfigException = type('EncoderConfigException', (EncoderException,), {})
EncoderRuntimeException = type('EncoderRuntimeException', (EncoderException,), {})
SettingConfigException = type('SettingConfigException', (EncoderException,), {})
SettingRuntimeException = type('SettingRuntimeException', (EncoderException,), {})


def q(v):
    return '"{}"'.format(v)


class Setting(ABC):
    name = None
    type = None
    allowed_options = {'default'}

    def __init__(self, config):
        if not config:
            config = {}
        self.config = config
        self.check_class_defaults()
        self.check_config()

    def check_class_defaults(self):
        if self.name is None:
            raise NotImplementedError(
                'Setting with its handler class name {} must have '
                'attribute `name` defined.'.format(self.__class__.__name__))
        if self.type is None:
            raise NotImplementedError(
                'Setting with its handler class name {} must have '
                'attribute `type` defined.'.format(self.__class__.__name__))

    def check_config(self):
        if not isinstance(self.config, dict):
            raise SettingConfigException('Setting {} must have its configuration to be a dictionary or undefined. '
                                         'It is currently {}.'.format(q(self.name), self.config.__class__.__name__))
        for option in self.config.keys():
            if option not in self.allowed_options:
                raise SettingConfigException('Cannot recognize option {} for setting {}. '
                                             'Supported setting: {}.'.format(q(option), q(self.name),
                                                                             ', '.join(self.allowed_options)))

    def describe(self):
        raise NotImplementedError()

    def encode_option(self, values):
        raise NotImplementedError()

    def decode_option(self, data):
        raise NotImplementedError()


class RangeSetting(Setting, ABC):
    relaxable = True
    freeze_range = False
    type = 'range'
    unit = ''

    def __init__(self, config):
        self.allowed_options.update({'min', 'max', 'step'})
        super().__init__(config)
        self.min = self.config.get('min', getattr(self, 'min', None))
        self.max = self.config.get('max', getattr(self, 'max', None))
        self.step = self.config.get('step', getattr(self, 'step', None))
        self.default = self.config.get('default', getattr(self, 'default', None))

    def check_config(self):
        super().check_config()
        default_min = getattr(self, 'min', None)
        default_max = getattr(self, 'max', None)
        default_step = getattr(self, 'step', None)
        minv = self.config.get('min', default_min)
        maxv = self.config.get('max', default_max)
        step = self.config.get('step', default_step)
        if minv is None:
            raise SettingConfigException(
                'No min value configured for setting {} in jvm encoder.'.format(q(self.name)))
        if maxv is None:
            raise SettingConfigException(
                'No max value configured for setting {} in jvm encoder.'.format(q(self.name)))
        if step is None:
            raise SettingConfigException(
                'No step value configured for setting {} in jvm encoder.'.format(q(self.name)))
        if not isinstance(minv, (int, float)):
            raise SettingConfigException('Min value must be a number in setting {} of jvm encoder. '
                                         'Found {}.'.format(q(self.name), q(minv)))
        if not isinstance(maxv, (int, float)):
            raise SettingConfigException('Max value must be a number in setting {} of jvm encoder. '
                                         'Found {}.'.format(q(self.name), q(maxv)))
        if not isinstance(step, (int, float)):
            raise SettingConfigException('Step value must be a number in setting {} of jvm encoder. '
                                         'Found {}.'.format(q(self.name), q(step)))
        if minv > maxv:
            raise SettingConfigException('Lower boundary is higher than upper boundary in setting {} '
                                         'of jvm encoder.'.format(q(self.name)))
        if minv != maxv:
            if step < 0:
                raise SettingConfigException('Step for setting {} must be a positive number.'
                                             ''.format(q(self.name)))
            if step == 0:
                raise SettingConfigException(
                    'Step for setting {} cannot be zero when min != max.'.format(q(self.name)))
        if step != 0 and (maxv - minv) % step > 0:
            raise SettingConfigException(
                'Step value for setting {} must allow to get from {} to {} in equal steps. Its current value is {}. '
                'The size of the last step would be {}.'.format(q(self.name), minv, maxv, step, (maxv - minv) % step))
        # Freeze range for change from config
        if self.freeze_range:
            if default_min is None:
                raise NotImplementedError('Min value for setting {} must be configured to allow '
                                          'freeze of the range.'.format(q(self.name)))
            if default_max is None:
                raise NotImplementedError('Max value for setting {} must be configured to allow '
                                          'freeze of the range.'.format(q(self.name)))
            if default_step is None:
                raise NotImplementedError('Max value for setting {} must be configured to allow '
                                          'freeze of the range.'.format(q(self.name)))
            c = self.config
            if c.get('min') or c.get('max') or c.get('step'):
                raise SettingConfigException('Cannot change min, max or step in setting {}.'.format(q(self.name)))
        # Relaxation of boundaries
        if self.relaxable is False:
            if default_min is None:
                raise NotImplementedError('Default min value for setting {} must be configured '
                                          'to disallow its relaxation.'.format(q(self.name)))
            elif minv < default_min:
                raise SettingConfigException('Min value for setting {} cannot be lower than {}. '
                                             'It is {} now.'.format(q(self.name),
                                                                    default_min, minv))
            if default_max is None:
                raise NotImplementedError('Default max value for setting {} must be configured '
                                          'to disallow its relaxation.'.format(q(self.name)))
            elif maxv > default_max:
                raise SettingConfigException('Max value for setting {} cannot be lower than {}. '
                                             'It is {} now.'.format(q(self.name), default_max, maxv))
            if default_step is None:
                raise NotImplementedError('Default step value for setting {} must be configured '
                                          'to disallow its change.'.format(q(self.name)))
            elif step % default_step > 0:
                raise SettingConfigException('Step value for setting {} must be multiple of provided default {}. '
                                             'It is {} now.'.format(q(self.name), default_step, step))

    def describe(self):
        descr = {
            'type': self.type,
            'min': self.min,
            'max': self.max,
            'step': self.step,
            'unit': self.unit,
        }
        if self.default is not None:
            descr['default'] = self.default
        return self.name, descr

    def validate_value(self, value):
        if value is None:
            raise SettingRuntimeException('No value provided for setting {}'.format(self.name))
        if not isinstance(value, (float, int)):
            raise SettingRuntimeException('Value in setting {} must be either integer or float. '
                                          'Found {}.'.format(q(self.name), q(value)))
        if value < self.min:
            raise SettingRuntimeException('Value {} is violating lower bound '
                                          'in setting {}'.format(q(value), q(self.name)))
        if value > self.max:
            raise SettingRuntimeException('Value {} is violating upper bound '
                                          'in setting {}'.format(q(value), q(self.name)))
        if self.min < self.max and self.step > 0 and (value - self.min) % self.step != 0:
            raise SettingRuntimeException('Value {} is violating step requirement '
                                          'in setting {}. Step is size {}'.format(q(value), q(self.name),
                                                                                  self.step))
        return value


class Encoder(ABC):

    def describe(self):
        raise NotImplementedError()

    def encode_multi(self, values):
        raise NotImplementedError()

    def decode_multi(self, data):
        raise NotImplementedError()


def load_encoder(encoder):
    if isinstance(encoder, str):
        try:
            return importlib.import_module('encoders.{}'.format(encoder)).Encoder
        except ImportError:
            raise ImportError('Unable to import encoder {}'.format(encoder))
        except AttributeError:
            raise AttributeError('Were not able to import encoder\'s class from encoders.{}'.format(encoder))
    return encoder


def validate_config(config):
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise EncoderConfigException('Configuration object for jvm encoder is expected to be a dictionary')
    if not config.get('name'):
        raise EncoderConfigException('No encoder name specified')
    return config


def encode(config, values):
    config = validate_config(config)
    encoder_klass = load_encoder(config['name'])
    encoder = encoder_klass(config)
    settings = encoder.describe()
    encodable = {name: values.get(name) for name in settings.keys()}
    return encoder.encode_multi(encodable), set(encodable)


def describe(config, data):
    config = validate_config(config)
    encoder_klass = load_encoder(config['name'])
    encoder = encoder_klass(config)
    settings = encoder.describe()
    decoded = encoder.decode_multi(data)
    descriptor = {name: {**setting, 'value': decoded[name]} for name, setting in settings.items()}
    return descriptor
