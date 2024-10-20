# Function to reconstruct the nested array from flattened list
define :reconstruct_array do |flattened_data|
  reconstructed = []
  current_sub_array = []
  
  flattened_data.each do |item|
    if item == "START"  # Start of a new sub-array
      reconstructed.push(current_sub_array) unless current_sub_array.empty?
      current_sub_array = []
    else
      current_sub_array.push(item)
    end
  end
  # Add the last sub-array (if any)
  reconstructed.push(current_sub_array) unless current_sub_array.empty?
  return reconstructed
end

# Function to play notes based on the incoming list
define :play_notes do |note_list|
  note_list.each do |note_data|
    if note_data.is_a?(Array) && note_data.length == 5
      type = note_data[0]     # Type (synth or sleep)
      instrument = note_data[1]     # Instrument name
      note = note_data[2]    # Note value
      duration = note_data[3]  # Duration/release
      volume = note_data[4]   # Amplitude
      
      if type == 'sleep'
        sleep duration
      else
        synth instrument.to_s, note: note.to_s, release: duration, amp: volume
      end
    end
  end
end

# Global variable to store the current sequence
set :current_sequence, []
set :sequence_updated, false

# Ambient background loop
live_loop :drifting_ambient do
  use_real_time
  note = sync "/osc*/ambient"
  use_synth :prophet
  play note: note[0].to_s, release: 10, attack: 1, cutoff: rrand(60, 90), amp: 0.15
end

# OSC listener to receive and update the sequence
live_loop :osc_listener do
  use_real_time
  data = sync "/osc*/synth"  # Listening for OSC messages
  
  if data.is_a?(Array)
    new_sequence = reconstruct_array(data)
    set :current_sequence, new_sequence  # Update the global sequence
    set :sequence_updated, true  # Signal that we have a new sequence
  else
    puts "Received incorrect format"
  end
end

# Continuous player loop
live_loop :sequence_player do
  # Check if we have a sequence to play
  current_sequence = get[:current_sequence]
  
  if current_sequence && !current_sequence.empty?
    # Reset the update flag if this is a new sequence
    if get[:sequence_updated]
      set :sequence_updated, false
      puts "Playing new sequence"
    end
    
    # Play through the sequence once
    play_notes(current_sequence)
  else
    # If no sequence available, wait a bit
    sleep 0.1
  end
end