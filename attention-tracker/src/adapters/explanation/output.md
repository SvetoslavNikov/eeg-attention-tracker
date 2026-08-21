```/Users/svetoslavnikov/lys/eeg-attention-tracker/attention-tracker/.venv/bin/python3.14 /Users/svetoslavnikov/lys/eeg-attention-tracker/attention-tracker/src/adapters/explanation/dump_session.py 

========================================================================
NPZ  /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/perceived_speech/audio_movie/EEG_RAW_study-perceivedspeech_sub-p33_desc-95afb90.npz
========================================================================
keys: ['time', 'data', 'channel_names', 'fs_hz', 'study_id', 'subject_id', 'source_snirf', 'measurement_date', 'measurement_time', 'impedance']

  time
    dtype=float64  shape=(281118,)
    first 3: [-0.11453271 -0.11253262 -0.11053276]
    last  3: [562.11451125 562.11651134 562.11851144]
    duration: 562.233 s
    median dt: 2.0001 ms
  data
    dtype=float32  shape=(281118, 4)
    first 3 rows:
      [ -261990.671875  -487945.3125    -932106.25     -1994023.375   ]
      [ -299045.375   -520703.6875  -999064.375  -2060350.625 ]
      [ -329526.     -549102.875 -1081207.625 -2142161.75 ]
    last row: [ -177929.703125  -351969.65625   -779292.75     -1444711.75    ]
    per-channel min / mean / max:
      ch0:  -3.794e+05  /  -1.592e+05  /  -3.106e+04
      ch1:  -6.001e+05  /  -3.434e+05  /  -2.369e+05
      ch2:  -1.104e+06  /  -9.024e+05  /  -7.014e+05
      ch3:  -2.164e+06  /  -1.61e+06  /  -1.418e+06
  channel_names
    dtype=object  shape=(4,)
    value=['AF4', 'AF3', 'FCz', 'CPz']
  fs_hz
    dtype=float64  shape=()
    value=500.000850050098
  study_id
    dtype=<U7  shape=()
    value='95afb90'
  subject_id
    dtype=<U3  shape=()
    value='P33'
  source_snirf
    dtype=<U56  shape=()
    value='study-perceivedspeech_sub-p33_desc-95afb90_MOMENTS.snirf'
  measurement_date
    dtype=<U10  shape=()
    value='2026-06-29'
  measurement_time
    dtype=<U13  shape=()
    value='15:29:56.116Z'
  impedance
    dtype=float32  shape=(281118, 4)
    min=0  max=0  mean=0

========================================================================
JSONL  /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/perceived_speech/audio_movie/perceived_speech_log_20260629_182907.jsonl
========================================================================
header comments (8):
  participant_id: P33
  experiment_name: perceived_speech
  device: nirs/flow2
  device_name: Flow2 Danube 187 Hoppip
  session_number: 55
  operator: (empty)
  notes: coughed during session
  portal_protocol_version: 1.0.0

events: 897
event_type counts:
    849  perceived_word
      6  functional_localizer_cue_start
      6  functional_localizer_cue_end
      5  functional_localizer_rest_start
      5  functional_localizer_rest_end
      4  kernel_phase
      3  escape_overlay
      1  session_started
      1  kernel_login
      1  sdk_streaming_status
      1  kortex_status
      1  kernel_start_recording_attempt
      1  kernel_start_recording_result
      1  start_experiment
      1  introduction_end
      1  baseline_start
      1  baseline_end
      1  functional_localizer_start
      1  functional_localizer_instructions_end
      1  functional_localizer_end
      1  task_start
      1  quit
      1  end_experiment
      1  awaiting_end_note
      1  kernel_stop_recording
      1  kernel_turn_off_lasers

phase-ish timeline (seconds after kernel_start_recording_result):
  t=    0.00s  kernel_start_recording_result  {'ok': True}
  t=    1.99s  baseline_start  {'duration_s': 60.0}
  t=   62.02s  baseline_end  {'duration_s': 60.0}
  t=   62.02s  functional_localizer_start  {'repeats': 3, 'left_duration_s': 15.0, 'right_duration_s': 15.0, 'rest_duration_s': 15.0, 'n_cues': 6}
  t=  228.17s  functional_localizer_end  {'repeats': 3, 'n_cues': 6}
  t=  230.52s  task_start  {'audio_topic': 'The_way_of_Kings_1_STORMLIGHT0101', 'audio_chunk': 'chunk_1_5minutes28seconds', 'audio_file': 'The_way_of_Kings_1_STORMLIGHT0101_part_1.wav', 'transcript_file': 'The_way_of_Kings_1_STORMLIGHT0101_part_1.json', 'audio_duration_s': 328.0, 'audio_samplerate': 16000, 'resume_from_ms': 0, 'replay': False}
  t=  558.74s  quit  {'reason': 'finished', 't_rel': 328.194}
  t=  559.16s  end_experiment  {}

sample events (up to 1 per type):
  [session_started] t=-48.94s  {}
  [kernel_phase] t=-48.94s  {'phase': 'starting_up'}
  [kernel_login] t=-28.88s  {'ok': True, 'study_url': 'https://portal.kernel.com/organizations/69e11c61-6636-4e39-bd2a-749370c98597/studies/10a99…'}
  [sdk_streaming_status] t=-8.59s  {'streaming': True}
  [kortex_status] t=-5.45s  {'available': True}
  [kernel_start_recording_attempt] t=-5.45s  {'participant_id': 'P33', 'session_number': 55}
  [kernel_start_recording_result] t=0.00s  {'ok': True}
  [start_experiment] t=0.00s  {}
  [introduction_end] t=1.99s  {}
  [baseline_start] t=1.99s  {'duration_s': 60.0}
  [baseline_end] t=62.02s  {'duration_s': 60.0}
  [functional_localizer_start] t=62.02s  {'repeats': 3, 'left_duration_s': 15.0, 'right_duration_s': 15.0, 'rest_duration_s': 15.0, 'n_cues': 6}
  [functional_localizer_instructions_end] t=63.01s  {}
  [functional_localizer_cue_start] t=63.02s  {'direction': 'right', 'duration_s': 15.0}
  [functional_localizer_cue_end] t=78.03s  {'direction': 'right', 'duration_s': 15.0, 'actual_duration_s': 15.017}
  [functional_localizer_rest_start] t=78.03s  {'duration_s': 15.0}
  [functional_localizer_rest_end] t=93.07s  {'duration_s': 15.0, 'actual_duration_s': 15.033}
  [functional_localizer_end] t=228.17s  {'repeats': 3, 'n_cues': 6}
  [task_start] t=230.52s  {'audio_topic': 'The_way_of_Kings_1_STORMLIGHT0101', 'audio_chunk': 'chunk_1_5minutes28seconds', 'audio_file': 'The_way_of_Kings_1_STORMLIGHT0101_part_1.wav', 'transcript_file': 'The_way_of_Kings_1_STORMLIGHT0101_part_1.json', 'audio_duration_s': 328.0, 'audio_samplerate': 16000, 'resume_from_ms': 0, 'replay': False}
  [perceived_word] t=230.66s  {'word': 'Sen', 'start_ms': 0, 'end_ms': 600, 'confidence': 1.0}
  [escape_overlay] t=442.96s  {'time_elapsed_s': 212.41, 'time_remaining_s': 115.6, 'screen_state': 'fixation'}
  [quit] t=558.74s  {'reason': 'finished', 't_rel': 328.194}
  [end_experiment] t=559.16s  {}
  [awaiting_end_note] t=559.17s  {'abnormal': False, 'reason': None}
  [kernel_stop_recording] t=561.36s  {'ok': True}
  [kernel_turn_off_lasers] t=561.41s  {'ok': True}

========================================================================
What adapters/lys.py keeps (EEGSession)
========================================================================
  source_path : /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/perceived_speech/audio_movie/EEG_RAW_study-perceivedspeech_sub-p33_desc-95afb90.npz
  subject_id  : P33
  study_id    : 95afb90
  ch_names    : ('AF4', 'AF3', 'FCz', 'CPz')
  fs          : 500.000850 Hz
  n_samples   : 281118
  duration    : 562.233 s
  data.shape  : (281118, 4)  dtype=float64
  time[0],[-1]: -0.114533, 562.118511
  phases (seconds on the EEG time axis):
    baseline    [    1.99,    62.02]  (60.0 s)
    localizer   [   62.02,   228.17]  (166.2 s)
    task        [  230.52,   558.74]  (328.2 s)

  dropped from the raw files on purpose:
    npz: impedance, source_snirf, measurement_date/time
    jsonl: words, game commands, audio paths, localizer cues, …
------------------------------------------------------------------------

========================================================================
NPZ  /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/perceived_speech/Bill_Ackman_part2/EEG_RAW_study-perceivedspeech_sub-p33_desc-f1f9380.npz
========================================================================
keys: ['time', 'data', 'channel_names', 'fs_hz', 'study_id', 'subject_id', 'source_snirf', 'measurement_date', 'measurement_time', 'impedance']

  time
    dtype=float64  shape=(635835,)
    first 3: [-0.04259372 -0.04059362 -0.03859377]
    last  3: [1271.62037563 1271.62237549 1271.62437558]
    duration: 1271.667 s
    median dt: 2.0001 ms
  data
    dtype=float32  shape=(635835, 4)
    first 3 rows:
      [  -60785.29296875   -69589.375       -469223.5        -1161074.125     ]
      [  -44552.02734375   -63673.49609375  -465268.84375    -1157483.75      ]
      [  -44891.05859375   -62323.2734375   -464352.59375    -1156717.125     ]
    last row: [   24147.390625   -44765.53125   -520929.5      -1436835.75    ]
    per-channel min / mean / max:
      ch0:  -8.858e+05  /  -4.945e+04  /  6.631e+05
      ch1:  -4e+05  /  -5.686e+04  /  1.03e+05
      ch2:  -1.078e+06  /  -4.464e+05  /  6.016e+05
      ch3:  -1.777e+06  /  -1.303e+06  /  -5.481e+04
  channel_names
    dtype=object  shape=(4,)
    value=['AF4', 'AF3', 'FCz', 'CPz']
  fs_hz
    dtype=float64  shape=()
    value=500.00040525574246
  study_id
    dtype=<U7  shape=()
    value='f1f9380'
  subject_id
    dtype=<U3  shape=()
    value='P33'
  source_snirf
    dtype=<U56  shape=()
    value='study-perceivedspeech_sub-p33_desc-f1f9380_MOMENTS.snirf'
  measurement_date
    dtype=<U10  shape=()
    value='2026-06-24'
  measurement_time
    dtype=<U13  shape=()
    value='12:35:09.188Z'
  impedance
    dtype=float32  shape=(635835, 4)
    min=0  max=0  mean=0

========================================================================
What adapters/lys.py keeps (EEGSession)
========================================================================
  source_path : /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/perceived_speech/Bill_Ackman_part2/EEG_RAW_study-perceivedspeech_sub-p33_desc-f1f9380.npz
  subject_id  : P33
  study_id    : f1f9380
  ch_names    : ('AF4', 'AF3', 'FCz', 'CPz')
  fs          : 500.000405 Hz
  n_samples   : 635835
  duration    : 1271.667 s
  data.shape  : (635835, 4)  dtype=float64
  time[0],[-1]: -0.042594, 1271.624376
  phases      : {}  (no jsonl, or no start/end pair found)

  dropped from the raw files on purpose:
    npz: impedance, source_snirf, measurement_date/time
    jsonl: words, game commands, audio paths, localizer cues, …
------------------------------------------------------------------------

========================================================================
NPZ  /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/zork_task/EEG_RAW_study-zorkdork_sub-p33_desc-bb05ebe.npz
========================================================================
keys: ['time', 'data', 'channel_names', 'fs_hz', 'study_id', 'subject_id', 'source_snirf', 'measurement_date', 'measurement_time', 'impedance']

  time
    dtype=float64  shape=(644381,)
    first 3: [-0.24664569 -0.2446456  -0.24264574]
    last  3: [1288.50894713 1288.51094723 1288.51294708]
    duration: 1288.760 s
    median dt: 2.0001 ms
  data
    dtype=float32  shape=(644381, 4)
    first 3 rows:
      [ -390584.875   -349969.8125  -780549.625  -1575022.625 ]
      [ -352495.90625  -323772.125    -702883.0625  -1495944.625  ]
      [ -364616.28125  -335890.875    -710266.125   -1503352.375  ]
    last row: [ -316269.46875  -334794.9375   -691970.25    -1230106.625  ]
    per-channel min / mean / max:
      ch0:  -4.523e+05  /  -3.467e+05  /  -2.447e+05
      ch1:  -3.949e+05  /  -2.97e+05  /  -2.004e+05
      ch2:  -8.931e+05  /  -7.598e+05  /  -6.005e+05
      ch3:  -1.7e+06  /  -1.361e+06  /  -1.141e+06
  channel_names
    dtype=object  shape=(4,)
    value=['AF4', 'AF3', 'FCz', 'CPz']
  fs_hz
    dtype=float64  shape=()
    value=500.0001579924107
  study_id
    dtype=<U7  shape=()
    value='bb05ebe'
  subject_id
    dtype=<U3  shape=()
    value='P33'
  source_snirf
    dtype=<U49  shape=()
    value='study-zorkdork_sub-p33_desc-bb05ebe_MOMENTS.snirf'
  measurement_date
    dtype=<U10  shape=()
    value='2026-06-29'
  measurement_time
    dtype=<U13  shape=()
    value='12:32:55.947Z'
  impedance
    dtype=float32  shape=(644381, 4)
    min=0  max=0  mean=0

========================================================================
JSONL  /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/zork_task/zork_task_log_20260629_153057.jsonl
========================================================================
header comments (8):
  participant_id: P33
  experiment_name: zork_task
  device: nirs/flow2
  device_name: Flow2 Danube 187 Hoppip
  session_number: 30
  operator: (empty)
  notes: (empty)
  portal_protocol_version: 1.0.0

events: 956
event_type counts:
    448  game_output
    137  state_snapshot
    136  decision_time
    136  user_command
     49  room_transition
      6  functional_localizer_cue_start
      6  functional_localizer_cue_end
      5  kernel_phase
      5  functional_localizer_rest_start
      5  functional_localizer_rest_end
      3  escape_overlay
      1  session_started
      1  kernel_login
      1  sdk_streaming_status
      1  kortex_status
      1  kernel_start_recording_attempt
      1  kernel_start_recording_result
      1  start_experiment
      1  introduction_end
      1  baseline_start
      1  baseline_end
      1  functional_localizer_start
      1  functional_localizer_instructions_end
      1  functional_localizer_end
      1  task_start
      1  game_start
      1  quit
      1  end_experiment
      1  awaiting_end_note
      1  kernel_stop_recording
      1  kernel_turn_off_lasers

phase-ish timeline (seconds after kernel_start_recording_result):
  t=    0.00s  kernel_start_recording_result  {'ok': True}
  t=    3.38s  baseline_start  {'duration_s': 60.0}
  t=   63.40s  baseline_end  {'duration_s': 60.0}
  t=   63.40s  functional_localizer_start  {'repeats': 3, 'left_duration_s': 15.0, 'right_duration_s': 15.0, 'rest_duration_s': 15.0, 'n_cues': 6}
  t=  231.87s  functional_localizer_end  {'repeats': 3, 'n_cues': 6}
  t=  233.48s  task_start  {'game_id': 'zork_infocom', 'world_version': 'frotz_zork1', 'initial_room_id': 'living_room', 'resumed': True}
  t= 1284.67s  quit  {'reason': 'ctrl_q', 'screen_state': 'game', 't_rel': 1051.163}
  t= 1285.14s  end_experiment  {}

sample events (up to 1 per type):
  [session_started] t=-119.52s  {}
  [kernel_phase] t=-119.51s  {'phase': 'starting_up'}
  [kernel_login] t=-99.46s  {'ok': True, 'study_url': 'https://portal.kernel.com/organizations/69e11c61-6636-4e39-bd2a-749370c98597/studies/643a8…'}
  [sdk_streaming_status] t=-5.98s  {'streaming': True}
  [kortex_status] t=-5.26s  {'available': True}
  [kernel_start_recording_attempt] t=-5.26s  {'participant_id': 'P33', 'session_number': 30}
  [kernel_start_recording_result] t=0.00s  {'ok': True}
  [start_experiment] t=0.00s  {}
  [introduction_end] t=3.38s  {}
  [baseline_start] t=3.38s  {'duration_s': 60.0}
  [baseline_end] t=63.40s  {'duration_s': 60.0}
  [functional_localizer_start] t=63.40s  {'repeats': 3, 'left_duration_s': 15.0, 'right_duration_s': 15.0, 'rest_duration_s': 15.0, 'n_cues': 6}
  [functional_localizer_instructions_end] t=66.64s  {}
  [functional_localizer_cue_start] t=66.66s  {'direction': 'right', 'duration_s': 15.0}
  [functional_localizer_cue_end] t=81.69s  {'direction': 'right', 'duration_s': 15.0, 'actual_duration_s': 15.032}
  [functional_localizer_rest_start] t=81.69s  {'duration_s': 15.0}
  [functional_localizer_rest_end] t=96.70s  {'duration_s': 15.0, 'actual_duration_s': 15.015}
  [functional_localizer_end] t=231.87s  {'repeats': 3, 'n_cues': 6}
  [task_start] t=233.48s  {'game_id': 'zork_infocom', 'world_version': 'frotz_zork1', 'initial_room_id': 'living_room', 'resumed': True}
  [game_start] t=233.49s  {'game_id': 'zork_infocom', 'world_version': 'frotz_zork1', 'initial_room_id': 'living_room', 'resumed': True}
  [game_output] t=233.49s  {'turn': 228, 'room_id': 'living_room', 'channel': 'main', 'text': 'Living Room'}
  [state_snapshot] t=233.49s  {'turn': 228, 'room_id': 'living_room', 'score': 103, 'inventory': [], 'room_description': 'Living Room\nYou are in the living room. There is a doorway to the east, a wooden door\nwith…', 'visible_objects': []}
  [decision_time] t=247.66s  {'turn': 229, 'decision_time_ms': 14160, 'command': 'i', 't_rel': 14.16}
  [user_command] t=247.66s  {'turn': 229, 'room_id': 'living_room', 'raw_input': 'i', 'normalized_verb': 'i', 'normalized_args': [], 't_rel': 14.16}
  [room_transition] t=282.94s  {'turn': 235, 'from_room': 'living_room', 'to_room': 'cellar', 'via': 'd', 't_rel': 49.433}
  [escape_overlay] t=990.36s  {'time_elapsed_s': 756.73, 'time_remaining_s': None, 'screen_state': 'game'}
  [quit] t=1284.67s  {'reason': 'ctrl_q', 'screen_state': 'game', 't_rel': 1051.163}
  [end_experiment] t=1285.14s  {}
  [awaiting_end_note] t=1285.14s  {'abnormal': False, 'reason': None}
  [kernel_stop_recording] t=1287.73s  {'ok': True}
  [kernel_turn_off_lasers] t=1287.79s  {'ok': True}

========================================================================
What adapters/lys.py keeps (EEGSession)
========================================================================
  source_path : /Users/svetoslavnikov/lys/eeg-attention-tracker/data/lys_data/zork_task/EEG_RAW_study-zorkdork_sub-p33_desc-bb05ebe.npz
  subject_id  : P33
  study_id    : bb05ebe
  ch_names    : ('AF4', 'AF3', 'FCz', 'CPz')
  fs          : 500.000158 Hz
  n_samples   : 644381
  duration    : 1288.760 s
  data.shape  : (644381, 4)  dtype=float64
  time[0],[-1]: -0.246646, 1288.512947
  phases (seconds on the EEG time axis):
    baseline    [    3.38,    63.40]  (60.0 s)
    localizer   [   63.40,   231.87]  (168.5 s)
    task        [  233.48,  1284.67]  (1051.2 s)

  dropped from the raw files on purpose:
    npz: impedance, source_snirf, measurement_date/time
    jsonl: words, game commands, audio paths, localizer cues, …
------------------------------------------------------------------------

Process finished with exit code 0```