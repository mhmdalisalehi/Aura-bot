```mermaid
flowchart TD
%% === Utility Functions ===
subgraph "workout_utils.py"
WU_calculate_rest_time["calculate_rest_time(exercise_type, intensity)"]
WU_calculate_intensity["calculate_intensity(goal, experience, week)"]
WU_convert_persian_to_english_weekday["convert_persian_to_english_weekday(persian_day)"]
WU_get_next_training_day["get_next_training_day(current_date, training_days)"]
WU_convert_day_to_date["convert_day_to_date(day_name, base_date)"]
WU_get_muscle_groups_for_split["get_muscle_groups_for_split(split_type)"]
WU_get_exercise_notes["get_exercise_notes(exercise, experience_level)"]
end

subgraph "date_converter.py"
DC_convert_persian_to_english_weekday["convert_persian_to_english_weekday(persian_day)"]
DC_convert_day_to_date["convert_day_to_date(day_name, base_date)"]
DC_get_next_training_day["get_next_training_day(current_date, training_days)"]
end

%% === Service Classes and Methods ===
subgraph "WorkoutGenerator"
WG_init["__init__"]
WG_initialize_managers["_initialize_managers"]
WG_validate_managers["_validate_managers"]
WG_prepare_exercise_data["_prepare_exercise_data"]
WG_format_mobility_exercises["_format_mobility_exercises"]
WG_get_mobility_duration["_get_mobility_duration"]
WG_get_mobility_notes["_get_mobility_notes"]
WG_adjust_workout["adjust_workout"]
WG_adjust_volume["_adjust_volume"]
WG_adjust_intensity["_adjust_intensity"]
WG_adjust_sequence["_adjust_sequence"]
end

subgraph "WorkoutPlanGenerator"
WPG_init["__init__"]
WPG_initialize_managers["_initialize_managers"]
WPG_validate_managers["_validate_managers"]
WPG_generate_deload_week["_generate_deload_week"]
WPG_adjust_plan["adjust_plan"]
WPG_adjust_volume["_adjust_volume"]
WPG_adjust_intensity["_adjust_intensity"]
WPG_adjust_sequence["_adjust_sequence"]
WPG_parse_duration["_parse_duration"]
end

subgraph "WorkoutValidator"
WS_init["__init__"]
WS_validate_initialization["_validate_initialization"]
WS_set_managers["set_managers"]
WS_validate_program["validate_program"]
WS_validate_structure["_validate_structure"]
WS_validate_exercise_structure["_validate_exercise_structure"]
WS_validate_exercise_balance["_validate_exercise_balance"]
WS_validate_volume["_validate_volume"]
WS_calculate_exercise_volume["_calculate_exercise_volume"]
WS_is_valid_exercise_volume["_is_valid_exercise_volume"]
WS_is_valid_muscle_volume["_is_valid_muscle_volume"]
WS_validate_sequence["_validate_sequence"]
WS_is_valid_exercise_sequence["_is_valid_exercise_sequence"]
WS_validate_limitations["_validate_limitations"]
WS_is_exercise_safe["_is_exercise_safe"]
WS_validate_recovery["_validate_recovery"]
WS_validate_mobility["_validate_mobility"]
WS_validate_workout["validate_workout"]
WS_validate_workout_structure["_validate_workout_structure"]
WS_validate_workout_exercises["_validate_workout_exercises"]
WS_validate_mobility_exercises["_validate_mobility_exercises"]
WS_is_valid_mobility_exercise["_is_valid_mobility_exercise"]
end

subgraph "WorkoutExporter"
WE_init["__init__"]
WE_export_to_json["export_to_json"]
WE_export_to_excel["export_to_excel"]
WE_export_to_text["export_to_text"]
WE_get_user_info["_get_user_info"]
WE_get_program_info["_get_program_info"]
WE_format_weekly_plan["_format_weekly_plan"]
WE_get_recovery_info["_get_recovery_info"]
WE_get_nutrition_tips["_get_nutrition_tips"]
WE_get_progress_tracking_info["_get_progress_tracking_info"]
WE_get_measurement_frequency["_get_measurement_frequency"]
WE_get_photo_guidelines["_get_photo_guidelines"]
WE_get_strength_tracking_guide["_get_strength_tracking_guide"]
WE_format_progress_tracking_info["_format_progress_tracking_info"]
WE_format_weekly_plan_text["_format_weekly_plan_text"]
WE_get_sleep_recommendation["_get_sleep_recommendation"]
WE_get_active_recovery_days["_get_active_recovery_days"]
WE_get_stretching_routine["_get_stretching_routine"]
WE_get_recovery_techniques["_get_recovery_techniques"]
WE_get_tracking_metrics["_get_tracking_metrics"]
end

subgraph "ExerciseScorer"
ES_calculate_exercise_score["calculate_exercise_score"]
ES_safety_score["_safety_score"]
ES_effectiveness_score["_effectiveness_score"]
ES_experience_score["_experience_score"]
ES_demographic_score["_demographic_score"]
ES_time_efficiency_score["_time_efficiency_score"]
ES_location_score["_location_score"]
ES_history_score["_history_score"]
end

subgraph "WorkoutVolumeManager"
VM_init["__init__"]
VM_calculate_volume["calculate_volume"]
VM_adjust_volume["adjust_volume"]
VM_muscle_priority["_muscle_priority"]
end

subgraph "MobilityManager"
MM_init["__init__"]
MM_get_mobility_exercises["get_mobility_exercises"]
MM_get_warmup_exercises["get_warmup_exercises"]
MM_get_cooldown_exercises["get_cooldown_exercises"]
MM_get_active_recovery_exercises["get_active_recovery_exercises"]
MM_get_target_areas_for_split["_get_target_areas_for_split"]
MM_filter_by_limitations["_filter_by_limitations"]
MM_adjust_for_demographics["_adjust_for_demographics"]
MM_prioritize_exercises["_prioritize_exercises"]
MM_get_max_difficulty["_get_max_difficulty"]
MM_update_recovery_needs["update_recovery_needs"]
MM_reset_mobility_status["reset_mobility_status"]
end

subgraph "RecoveryManager"
RM_init["__init__"]
%% ...other methods...
end

subgraph "SplitRotationManager"
SRM_get_optimal_split["get_optimal_split"]
SRM_update_split_if_needed["update_split_if_needed"]
end

subgraph "WeightCalculator"
WC_class["class WeightCalculator (stub)"]
end

%% === Split Strategies and Methods ===
subgraph "BroSplitStrategy"
BS_generate["generate"]
BS_build_muscle_day["_build_muscle_day"]
BS_build_muscle_exercises["_build_muscle_exercises"]
BS_apply_advanced_techniques["_apply_advanced_techniques"]
BS_get_technique_notes["_get_technique_notes"]
BS_adjust_exercise_volume["_adjust_exercise_volume"]
BS_build_hybrid_day["_build_hybrid_day"]
BS_create_exercise_entry["_create_exercise_entry"]
BS_calculate_rest_time["_calculate_rest_time"]
BS_generate_exercise_notes["_generate_exercise_notes"]
BS_get_volume_for_muscle["_get_volume_for_muscle"]
BS_select_secondary_exercise["_select_secondary_exercise"]
BS_get_user_weak_points["_get_user_weak_points"]
BS_select_cardio_protocol["_select_cardio_protocol"]
BS_build_cardio_protocol["_build_cardio_protocol"]
end

subgraph "PushPullLegsSplitStrategy"
PPL_generate["generate"]
PPL_build_day_plan["_build_day_plan"]
PPL_get_warmup["_get_warmup"]
PPL_get_cooldown["_get_cooldown"]
PPL_add_warmup_cooldown["_add_warmup_cooldown"]
PPL_validate_split_schedule["_validate_split_schedule"]
PPL_validate_volume["_validate_volume"]
PPL_adjust_program["_adjust_program"]
PPL_add_exercise["_add_exercise"]
PPL_adjust_exercise_scheduling["_adjust_exercise_scheduling"]
end

subgraph "UpperLowerSplitStrategy"
ULS_generate["generate"]
ULS_build_day_plan["_build_day_plan"]
ULS_build_muscle_exercises["_build_muscle_exercises"]
ULS_build_focus_area_exercises["_build_focus_area_exercises"]
ULS_apply_advanced_techniques["_apply_advanced_techniques"]
ULS_get_technique_notes["_get_technique_notes"]
ULS_adjust_exercise_volume["_adjust_exercise_volume"]
ULS_get_warmup["_get_warmup"]
ULS_get_cooldown["_get_cooldown"]
ULS_create_exercise_entry["_create_exercise_entry"]
ULS_calculate_rest_time["_calculate_rest_time"]
ULS_add_warmup_cooldown["_add_warmup_cooldown"]
ULS_validate_volume["_validate_volume"]
ULS_adjust_program["_adjust_program"]
end

subgraph "FullBodySplitStrategy"
FBS_generate["generate"]
FBS_apply_advanced_techniques["_apply_advanced_techniques"]
FBS_get_technique_notes["_get_technique_notes"]
FBS_adjust_exercise_volume["_adjust_exercise_volume"]
FBS_get_warmup["_get_warmup"]
FBS_get_cooldown["_get_cooldown"]
FBS_validate_day_plan["_validate_day_plan"]
end

%% === Relationships and Calls ===
WG_prepare_exercise_data --> WU_calculate_rest_time
WG_prepare_exercise_data --> WU_calculate_intensity
WG_prepare_exercise_data --> WU_get_exercise_notes

WPG_generate_deload_week --> WU_convert_persian_to_english_weekday
WPG_generate_deload_week --> WU_get_next_training_day
WPG_generate_deload_week --> WU_convert_day_to_date

WE_export_to_json --> WE_get_user_info
WE_export_to_json --> WE_get_program_info
WE_export_to_json --> WE_format_weekly_plan
WE_export_to_json --> WE_get_recovery_info
WE_export_to_json --> WE_get_nutrition_tips
WE_export_to_json --> WE_get_progress_tracking_info

ES_calculate_exercise_score --> ES_safety_score
ES_calculate_exercise_score --> ES_effectiveness_score
ES_calculate_exercise_score --> ES_experience_score
ES_calculate_exercise_score --> ES_demographic_score
ES_calculate_exercise_score --> ES_time_efficiency_score
ES_calculate_exercise_score --> ES_location_score
ES_calculate_exercise_score --> ES_history_score

BS_generate --> BS_build_muscle_day
BS_build_muscle_day --> BS_build_muscle_exercises
BS_build_muscle_day --> BS_apply_advanced_techniques
BS_build_muscle_day --> BS_get_technique_notes
BS_build_muscle_day --> BS_adjust_exercise_volume
BS_build_muscle_day --> BS_create_exercise_entry
BS_build_muscle_day --> BS_calculate_rest_time
BS_build_muscle_day --> BS_generate_exercise_notes

PPL_generate --> PPL_build_day_plan
PPL_build_day_plan --> PPL_get_warmup
PPL_build_day_plan --> PPL_get_cooldown
PPL_build_day_plan --> PPL_add_warmup_cooldown

ULS_generate --> ULS_build_day_plan
ULS_build_day_plan --> ULS_build_muscle_exercises
ULS_build_day_plan --> ULS_build_focus_area_exercises
ULS_build_day_plan --> ULS_apply_advanced_techniques
ULS_build_day_plan --> ULS_get_technique_notes
ULS_build_day_plan --> ULS_adjust_exercise_volume
ULS_build_day_plan --> ULS_get_warmup
ULS_build_day_plan --> ULS_get_cooldown
ULS_build_day_plan --> ULS_create_exercise_entry
ULS_build_day_plan --> ULS_calculate_rest_time

FBS_generate --> FBS_apply_advanced_techniques
FBS_generate --> FBS_get_technique_notes
FBS_generate --> FBS_adjust_exercise_volume
FBS_generate --> FBS_get_warmup
FBS_generate --> FBS_get_cooldown
FBS_generate --> FBS_validate_day_plan

%% Utility function cross-links
WU_convert_persian_to_english_weekday -- same as --> DC_convert_persian_to_english_weekday
WU_convert_day_to_date -- same as --> DC_convert_day_to_date
WU_get_next_training_day -- same as --> DC_get_next_training_day

class WU_calculate_rest_time,WU_calculate_intensity,WU_convert_persian_to_english_weekday,WU_get_next_training_day,WU_convert_day_to_date,WU_get_muscle_groups_for_split,WU_get_exercise_notes,DC_convert_persian_to_english_weekday,DC_convert_day_to_date,DC_get_next_training_day util
classDef util fill:#ffe,stroke:#333,stroke-width:1px
classDef class fill:#bbf,stroke:#333,stroke-width:1px
classDef method fill:#fff,stroke:#333,stroke-width:1px
```
