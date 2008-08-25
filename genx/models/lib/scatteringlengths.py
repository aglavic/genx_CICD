''' A library for handling optical constants and scattering lengths
in an efficent way. Based on a base class database which is subclassed
for each case.
Programmer: Matts Bjorck
Last changed: 2008-08-22
'''

import numpy as np
import re

#==============================================================================
class Database(object):
    '''A database class where object memebers are dynamically acessed
    and stored. I.e. the constants are only looked up when needed.
    '''
    def __init__(self):
        ''' __init__(self) --> None
        '''
        object.__setattr__(self, 'stored_values', {})
        
    def __getattribute__(self, name):
        '''__getattr__(self, name) --> object
        
        Looks up and returns the attribure name
        '''
        name = name.lower()
        stored_values = object.__getattribute__(self, 'stored_values')
        if stored_values.has_key(name):
            return stored_values[name]
        else:
            try:
                stored_values[name] = object.__getattribute__(self,\
                        'lookup_value')(name)
            except (LookupError, IOError), e:
                raise LookupError('The name %s does not exist in the'\
                    'database'%name)
            return stored_values[name]
        
    def __setattr__(self, name, value):
        '''__setattr__(self, name) --> None
        
        Just overlaoding the setattribute so a object cant be set.
        '''
        raise TypeError('This object does not support assignements')
    
    def lookup_value(self, name):
        '''lookup_value(self, name) --> object
        
        Used to (externally) lookup a value in a database to be inserted in
        local one for this object.
        '''
        print 'Looking up value'
        return 1
    
    def reset_database(self, name):
        '''reset_database(self, name) --> None
        
        Resets the internal database
        '''
        stored_values = object.__getattribute__(self, 'stored_values')
        stored_values = {}

#==============================================================================
class FormFactor(Database):
    ''' A database for the x-ray formfactor which includes the 
    anomulous part as well as the angle dependent part. The object will
    return a function of sin(theta)/lambda
    '''
    def __init__(self, wavelength, f_calc):
        '''__init__(self, wavelength, f_calc) --> None
        
        wavelength [float] the wavelength of the radiation in AA, f_calc a 
        function which calculates (lookup the scattering factor)
        '''
        Database.__init__(self)
        object.__setattr__(self, 'wavelength', wavelength)
        object.__setattr__(self, 'f_calc', f_calc)
        
    def set_wavelength(self, wavelength):
        '''set_wavelength(self, wavelength) --> None
        
        sets the wavelength of the database. This will reset the 
        all the values. I.e when called each value will be reloaded
        '''
        # First check so we actually change the wavelength ...
        if abs(wavelength\
            - object.__setattr__(self, 'wavelength', wavelength)) > 1e-10:
            object.__setattr__(self, 'wavelength', wavelength)
            object.__getattribute__(self, 'reset_database')()
        
    def __getattribute__(self, name):
        '''__getattribute__(self, name) --> value
        
        Finds and returns a attribute
        '''
        if name == 'set_wavelength':
            return object.__getattribute__(self, 'set_wavelength')
        else:
            return Database.__getattribute__(self, name)
        
    def lookup_value(self, name):
        '''lookup_value(self, name) --> f [function]
        
        looks up a value in the external database
        '''
        wl = object.__getattribute__(self, 'wavelength')
        return object.__getattribute__(self, 'f_calc')(name, wl)
    
#==============================================================================
class ScatteringLength(Database):
    ''' A simpler version of the database where everything is loaded at once
    good for simple and small databases. I.e the scatteringlength for
    a neutron which is largely wavelength independent.
    '''
    def __init__(self, values):
        '''__init__(self, values) --> None
        
        values is a dictonary of key value pairs that are used in the database.
        '''
        Database.__init__(self)
        object.__setattr__(self, 'stored_values', values)
        
    def lookup_value(self, name):
        raise LookupError('The element %s does not exist in the database'%name)
    
#==============================================================================
# Function to load databases and or values


def load_f0dabax(filename):
    '''load_dabax(filename) --> f0 (dictonary)
    
    loads a dabax file with f0 values and return a dictonary with 
    f0(sin(theta)/lambda) for the element given by the key name.
    '''
    def create_f(a, b, c):
        def f(sin_over_lambda):
            '''f(sin_over_lambda) --> float
            
            The atomic form factor for x-rays. The non-dispertive part.
            '''
            return c + sum(a[:, np.newaxis]*np.exp(-b[:, np.newaxis]\
                *sin_over_lambda**2), 0)
        return f

    f = open(filename)
    real_label = ''
    temp_dict = {}
    for line in f.readlines():
        # Get the label for each line
        if line[0]=='#':
            label=line[1]
            ret=line[1:-1]
        else:
            label='D'
            ret=line[:-1]
        # Gets the real label, atom name
        if label == 'S':
            real_label = ret.split()[-1]
        # The row contains data
        if label == 'D':
            temp_dict[real_label.lower()] = map(lambda x: float(x),ret.split())
    
    f0={}    
    for key in temp_dict.keys():
        temp = temp_dict[key]
        # change the name to not have operators...
        if key[-1] == '-':
            key = key[:-1] + 'm'
        if key[-1] == '+':
            key = key[:-1] + 'p'
        f0[key] = create_f(np.array(temp[:4]), np.array(temp[5:]), temp[4])
    return f0

def create_fp_lookup(path):
    '''create_f_lookup(filename) --> lookup_func(name, wavelength)
    
    Creates a lookup function to lookup element names and returns a function
    that yields dispersive scattering factors at Q = 0. NOTE wavelengths in AA
    '''
    def lookup_func(name, wavelength):
        '''lookup_func(name, wavelength) --> fp = f1 - 1.0J*f2
        
        looksup the scattering factors for a given wavelength given in AA for
        a element (note that the databases does not support ions). 
        The data given is the dispersive part + f0 (non dispersive) at Q = 0.
        '''
        e, f1, f2 = np.loadtxt(path + '%s.nff'%name.lower(), skiprows = 1,\
                unpack = True)
        energy = 1239.842/wavelength*10
        if energy >= e[-2] or energy <= e[1]:
            raise ValueError('The energy/wavelength is outside the databse'\
                + 'range, the energy should be inside [%f,%f] '%(e[1],e[-2]))
        pos1 = np.argmin(abs(e - energy))
        if pos1 + 1 < e.shape[0] and pos1 - 1 < e.shape[0]:
            if abs(e[pos1 + 1] - energy) > abs(e[pos1 - 1] - energy):
                pos2 = pos1 -1
            else:
                pos2 = pos1 + 1
        # A quick linear interpolation:
        f1_e = (energy - e[pos1])*(f1[pos2] - f1[pos1])/(e[pos2] - e[pos1])\
                + f1[pos1]
        f2_e = (energy - e[pos1])*(f2[pos2] - f2[pos1])/(e[pos2] - e[pos1])\
                + f2[pos1]
        
        return f1_e - 1.0J*f2_e
    return lookup_func

def create_f_lookup(lookup_fp, f0):
    '''create_f_lookup(lookup_fp, f0) --> lookup_func(name, wavelength)
    
    combines a f0 dictonary [dict] witht the lookup function for the
     anoumoulous scattering factors. Note that it is assumed that lookup_fp 
    is a function on the form lookup_fp(name, wavelength) --> f1 - 1.0Jf2
    where name is the name of the element!
    '''
    def lookup_func(name, wavelength):
        ''' Looks up the total angle dependent form factor 
        f = f0 + f1 + 1.0J*f2 of element name. This dispersive part
        is independent on the ionicity but f0 not.
        '''
        # Check if name corrspond to an ion
        element = None
        if len(name) > 1:
            if name[-2].isdigit():
                element = name[:-2]
            else:
                element = name
        else:
            element = name
        # Remove the non dispersive part for the given element
        fp = lookup_fp(element, wavelength) - f0[element](0)
        f0_name = f0[name]
        def f(sin_over_lambda):
            return f0_name(sin_over_lambda) + fp
        
        return f
    
    return lookup_func