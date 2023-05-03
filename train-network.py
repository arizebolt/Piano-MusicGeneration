import glob   # Retrieve files
import pickle # Serialize notes
import numpy  # Reshape and normalize input data

import music21
import keras.models as kmodel
import keras.layers as klayer
import keras.utils as utils
import keras.callbacks as callback

# 12 Pitches - Changes with respect to key
# C C# D D# E F F# G G# A A# B  C
# C Db D Eb E F Gb G Ab A Bb B  C
# 0 1  2 3  4 5 6  7 8  9 10 11 12

# Chords are parsed normal order
# Does not account for inversions / octave displacements

LSTM_UNITS = 512
RECURRENT_DROPOUT_RATE = 0.3
DROPOUT_RATE = 0.3

HIDDEN_LAYER_ACTIVATION_FUNCTION = "relu"
OUTPUT_LAYER_ACTIVATION_FUNCTION = "softmax"

DENSE_UNITS = 256

LOSS_FUNCTION = "categorical_crossentropy"
OPTIMIZER = "rmsprop"

def get_notes(directory):

    """
    Store individual notes and chords in a list
    And write it to a file at last
    """

    notes = list()

    # Process Midi file in the given directory
    # Get all notes and chords
    for file in glob.glob(directory):
        print("Parsing file %s" % file)
        parsed_midi = music21.converter.parse(file)

        try:
            # Midi file has more than one instrument
            # Instrument at index 0 probably has melody line
            instrument_parts = music21.instrument.partitionByInstrument(parsed_midi)
            notes_by_instrument = instrument_parts.parts[0].recurse()
        except:
            # Midi file is monophonic
            notes_by_instrument = parsed_midi.flat.notes
    
        # Convert notes / chords to string and append to notes
        for structure in notes_by_instrument:
            if isinstance(structure, music21.note.Note):
                notes.append(str(structure.pitch))
            elif isinstance(structure, music21.chord.Chord):
                # Return notes in normal order
                # Normal order representation of C Major triad - [0, 4, 7]
                notes.append(".".join(map(str, structure.normalOrder)))

    # Open a file called 'notes' in write binary mode 
    # and save the notes data to it using pickle
    with open('data/notes', 'wb') as file:
        pickle.dump(notes, file)

    return notes


def prepare_sequences(notes, num_pitch_classes):
    """
    Prepare the sequences used by the Neural Network
    """

    # Define the sequence length
    sequence_length = 100

    # Get all unique pitch names in the notes
    pitch_names = sorted(set(note for note in notes))

    # Create a dictionary to map pitch names to integer values
    pitch_to_int = dict((pitch, number) for number, pitch in enumerate(pitch_names))

    # Create input and output sequences for the neural network
    # Every sequence in input_sequences is sequence_length long.
    # Output sequence has the output that should be after input.

    input_sequences = list()
    output_sequence = list()

    # Generate input sequences and their corresponding outputs
    # Run till len(notes) - sequence_length to get every combination
    #   without errors.
    for i in range(0, len(notes) - sequence_length):
        sequence_in = notes[i:i + sequence_length]
        sequence_out = notes[i + sequence_length]
        input_sequences.append([pitch_to_int[pitch] for pitch in sequence_in])
        output_sequence.append(pitch_to_int[sequence_out])

    num_sequences = len(input_sequences)

    # Reshape the input sequences for use with LSTM layers
    input_sequences = numpy.reshape(input_sequences, (num_sequences, sequence_length, 1))

    # Normalize the input sequences
    input_sequences = input_sequences / float(num_pitch_classes)

    # Convert output sequences to categorical data
    output_sequence = utils.to_categorical(output_sequence)

    return (input_sequences, output_sequence)

# from keras.layers import LSTM, BatchNormalization, Dropout, Dense, Activation

def create_network(input_data, num_classes):
    """
    Create a neural network model for music generation.
    
    Args:
        input_data: A numpy array of shape (num_samples, sequence_length, num_features)
            representing the input data for the network.
        num_classes: An integer indicating the number of output classes (i.e. unique
            elements in the input data).
    
    Returns:
        A compiled Keras Sequential model representing the neural network.
    """

    # Define the model architecture
    model = kmodel.Sequential()
    model.add(klayer.LSTM(units=LSTM_UNITS, input_shape=(input_data.shape[1], input_data.shape[2]),
                   recurrent_dropout=RECURRENT_DROPOUT_RATE, return_sequences=True))
    model.add(klayer.LSTM(units=LSTM_UNITS, return_sequences=True, recurrent_dropout=RECURRENT_DROPOUT_RATE))
    model.add(klayer.LSTM(units=LSTM_UNITS))
    model.add(klayer.BatchNormalization())
    model.add(klayer.Dropout(rate=DROPOUT_RATE))
    model.add(klayer.Dense(units=DENSE_UNITS))
    model.add(klayer.Activation(HIDDEN_LAYER_ACTIVATION_FUNCTION))
    model.add(klayer.BatchNormalization())
    model.add(klayer.Dropout(rate=DROPOUT_RATE))
    model.add(klayer.Dense(units=num_classes))
    model.add(klayer.Activation(OUTPUT_LAYER_ACTIVATION_FUNCTION))

    # Compile the model
    model.compile(loss=LOSS_FUNCTION, optimizer=OPTIMIZER)
    
    return model
