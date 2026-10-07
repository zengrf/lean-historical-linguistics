import Comparative
import Historical

#print axioms Historical.SourceScope.run_append
#print axioms Historical.SourceScope.path_composition
#print axioms Historical.SourceScope.path_associativity
#print axioms Historical.SourceScope.indistinguishable_paths
#print axioms Historical.CaseStudy.retrieval_correct
#print axioms Historical.CaseStudy.retrieval_sound
#print axioms Historical.CaseStudy.retrieval_complete
#print axioms Historical.CaseStudy.retrieval_mono
#print axioms Historical.CaseStudy.retrieval_empty_iff
#print axioms Historical.CaseStudy.forward_certificate_accepted

#print axioms Comparative.run_append
#print axioms Comparative.derives_iff_run
#print axioms Comparative.checkTrace_sound
#print axioms Comparative.checkTrace_complete
#print axioms Comparative.fits_mono
#print axioms Comparative.fits_of_equivalent
#print axioms Comparative.mem_reconstruct_iff
#print axioms Comparative.reconstruction_correct
#print axioms Comparative.reconstruct_mono
#print axioms Comparative.Examples.rule_order_matters
#print axioms Comparative.Examples.valid_certificate
#print axioms Comparative.Examples.corrupted_certificate_rejected
#print axioms Comparative.Examples.missing_step_rejected
#print axioms Comparative.Examples.extra_step_rejected
#print axioms Comparative.Examples.distinct_protoforms
#print axioms Comparative.Examples.merger_ambiguity
#print axioms Comparative.Examples.finite_reconstruction_keeps_ambiguity
#print axioms Comparative.Examples.fits_checker_reflects
#print axioms Comparative.Patterns.compatible_is_not_transitive
#print axioms Comparative.Patterns.missing_is_not_gap
#print axioms Comparative.Patterns.missing_alone_is_not_support
#print axioms Comparative.Patterns.independent_choices_overgenerate

#print axioms Historical.replay_iff_chain
#print axioms Historical.renormalize_preserves_original
#print axioms Historical.renormalize_preserves_choices
#print axioms Historical.missing_ne_gap
#print axioms Historical.cell_json_roundtrip

#print axioms Historical.Rules.emits_iff_outputAt
#print axioms Historical.Rules.scan_eq_iff
#print axioms Historical.Rules.pass_iff_apply
#print axioms Historical.Rules.pass_deterministic
#print axioms Historical.Rules.outputAt_length_le
#print axioms Historical.Rules.scan_length_le
#print axioms Historical.Rules.applyRule_length_le
#print axioms Historical.Rules.morpheme_copied
#print axioms Historical.Certificates.checkTrace_iff
#print axioms Historical.Certificates.checkTrace_sound
#print axioms Historical.Certificates.checkTrace_complete
#print axioms Historical.Certificates.derives_iff_run
#print axioms Historical.Certificates.trace_implies_derives
#print axioms Historical.Certificates.run_append
#print axioms Historical.Certificates.canonical_trace_accepted
#print axioms Historical.Certificates.derivation_iff_certificate
#print axioms Historical.RuleInput.checkDossier_iff

#print axioms Historical.Alignment.removeGaps_iff
#print axioms Historical.Alignment.checkRow_iff
#print axioms Historical.Alignment.accepted_row_recovers
#print axioms Historical.Alignment.missing_is_not_erased
#print axioms Historical.Alignment.missing_row_ne_empty
#print axioms Historical.Alignment.checkAlignment_iff
#print axioms Historical.Alignment.accepted_alignment_preserves_rows
#print axioms Historical.Alignment.accepted_alignment_preserves_absence
#print axioms Historical.Alignment.accepted_alignment_has_material
#print axioms Historical.Correspondence.cellAgrees_iff
#print axioms Historical.Correspondence.sharedSound_iff
#print axioms Historical.Correspondence.noConflict_iff
#print axioms Historical.Correspondence.hasShared_iff
#print axioms Historical.Correspondence.compatible_iff
#print axioms Historical.Correspondence.missing_only_no_support
#print axioms Historical.Correspondence.unknown_only_no_support
#print axioms Historical.Correspondence.gap_only_no_support
#print axioms Historical.Correspondence.mem_distinctUnits
#print axioms Historical.Correspondence.distinctUnits_nodup
#print axioms Historical.Correspondence.mem_supportUnits
#print axioms Historical.Correspondence.checkClique_iff
#print axioms Historical.Correspondence.checkGroup_iff
#print axioms Historical.Correspondence.accepted_group_pairwise
#print axioms Historical.Correspondence.accepted_group_support
#print axioms Historical.Correspondence.checkPartition_iff
#print axioms Historical.Correspondence.accepted_partition_exactly_once
#print axioms Historical.Correspondence.accepted_partition_groups_valid
#print axioms Historical.Correspondence.compatibility_not_transitive
#print axioms Historical.Correspondence.nontransitive_merge_rejected
#print axioms Historical.Correspondence.missing_differs_from_gap
#print axioms Historical.Correspondence.disjoint_observations_not_support
#print axioms Historical.Correspondence.repeated_unit_not_extra_support
#print axioms Historical.CorrespondenceInput.dataAccepted_iff
#print axioms Historical.CorrespondenceInput.accepted_data_recovers_row
#print axioms Historical.CorrespondenceInput.dossierAccepted_iff

#print axioms Historical.Reconstruction.mem_wordsExact
#print axioms Historical.Reconstruction.length_prefixed
#print axioms Historical.Reconstruction.length_wordsExact
#print axioms Historical.Reconstruction.length_wordsUpTo
#print axioms Historical.Reconstruction.mem_wordsUpTo
#print axioms Historical.Reconstruction.mem_protoWords
#print axioms Historical.Reconstruction.cellMatches_iff
#print axioms Historical.Reconstruction.cellsMatch_iff
#print axioms Historical.Reconstruction.formMatches_iff
#print axioms Historical.Reconstruction.checkObservation_iff
#print axioms Historical.Reconstruction.fits_iff
#print axioms Historical.Reconstruction.mem_space
#print axioms Historical.Reconstruction.accepts_iff
#print axioms Historical.Reconstruction.reconstruction_correct
#print axioms Historical.Reconstruction.candidate_sound
#print axioms Historical.Reconstruction.candidate_complete
#print axioms Historical.Reconstruction.alternatives_remain_joint
#print axioms Historical.Reconstruction.mem_prefixResults
#print axioms Historical.Reconstruction.prefix_results_sound
#print axioms Historical.Reconstruction.prefix_results_in_space
#print axioms Historical.Reconstruction.prefixComplete_iff
#print axioms Historical.Reconstruction.completed_prefix_eq
#print axioms Historical.Reconstruction.completed_search_correct
#print axioms Historical.Reconstruction.completed_empty_iff
#print axioms Historical.Reconstruction.candidate_trace_accepted
#print axioms Historical.Reconstruction.missing_form_unconstrained
#print axioms Historical.Reconstruction.present_empty_differs_from_missing
#print axioms Historical.Reconstruction.unknown_is_one_segment
#print axioms Historical.Identifiability.equivalent_refl
#print axioms Historical.Identifiability.equivalent_symm
#print axioms Historical.Identifiability.equivalent_trans
#print axioms Historical.Identifiability.observation_from_prediction
#print axioms Historical.Identifiability.equivalent_fits
#print axioms Historical.Identifiability.fits_mono
#print axioms Historical.Identifiability.missing_is_weaker
#print axioms Historical.Identifiability.observes_refinement
#print axioms Historical.Identifiability.fits_refinement
#print axioms Historical.Identifiability.mem_reconstructWords
#print axioms Historical.Identifiability.reconstruction_mono
#print axioms Historical.Identifiability.reconstruction_refinement
#print axioms Historical.Identifiability.equivalent_membership
#print axioms Historical.Identifiability.merger_is_indistinguishable
#print axioms Historical.Identifiability.merger_retains_both_ancestors
#print axioms Historical.Identifiability.linked_alternatives_do_not_license_hybrids
#print axioms Historical.Identifiability.unexamined_empty_is_not_exhaustion
#print axioms Historical.ReconstructionInput.m3_projection_recovers
#print axioms Historical.ReconstructionInput.checked_reconstruction_iff
#print axioms Historical.ReconstructionInput.checked_candidate_correct

#print axioms Historical.Research.fits_iff
#print axioms Historical.Research.fits_mono
#print axioms Historical.Research.anyFits_iff
#print axioms Historical.Research.minimalConflict_iff
#print axioms Historical.Research.minimal_conflict_proper_subset
#print axioms Historical.Research.mem_subsets
#print axioms Historical.Research.reported_conflict_sound
#print axioms Historical.Research.conflicts_complete_in_enumeration
#print axioms Historical.Research.full_conflict_enumeration_correct
#print axioms Historical.Research.equivalent_refl
#print axioms Historical.Research.equivalent_symm
#print axioms Historical.Research.equivalent_trans
#print axioms Historical.Research.class_members_correct
#print axioms Historical.Research.order_enumeration_correct
#print axioms Historical.Research.order_respects_constraints
#print axioms Historical.Paradigm.tone_derivation_iff
#print axioms Historical.Paradigm.realization_correct
#print axioms Historical.Paradigm.realization_deterministic
#print axioms Historical.Paradigm.agrees_iff
#print axioms Historical.Paradigm.paradigm_reconstruction_correct

#print axioms Historical.Compile.output_independent

#print axioms Historical.Compile.scan_compiles

#print axioms Historical.Compile.rule_compiles

#print axioms Historical.Compile.run_nil

#print axioms Historical.Compile.run_append

#print axioms Historical.Compile.laws_compile

#print axioms Historical.Compile.image_compile

#print axioms Historical.Compile.compile_correct

#print axioms Historical.Inverse.consumeCells_correct

#print axioms Historical.Inverse.consume_correct

#print axioms Historical.Inverse.residual_correct

#print axioms Historical.Inverse.allows_nil

#print axioms Historical.Inverse.allows_cons

#print axioms Historical.Inverse.inverse_correct

#print axioms Historical.SearchGraph.faithful_at

#print axioms Historical.SearchGraph.graph_correct

#print axioms Historical.SearchGraph.inverse_machine_correct

#print axioms Historical.SearchGraph.checked_inverse_complete

#print axioms Historical.PrefixSearch.reference_machine_correct

#print axioms Historical.PrefixSearch.reference_graph_correct

#print axioms Historical.Protolexicon.product_correct

#print axioms Historical.Protolexicon.protolexicon_correct

#print axioms Historical.Protolexicon.solutions_correct

#print axioms Historical.Protolexicon.one_model_for_all_words

#print axioms Historical.Protolexicon.empty_entry_excludes_model

#print axioms Historical.LexiconInput.compiled_reflexes_correct

#print axioms Historical.LexiconInput.compiled_request_complete

#print axioms Historical.LexiconInput.reference_request_complete
