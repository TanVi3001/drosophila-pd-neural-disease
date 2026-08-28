from drosophila_pd_neural.models import DiseaseProfile, NeuralParameters


def test_profile_interpolates_only_declared_burden_curve() -> None:
    profile = DiseaseProfile(
        condition_id="demo",
        gene_model="alpha_synuclein",
        seed=3,
        full_burden=NeuralParameters(presynaptic_gain=0.5, noise_std=0.2),
        burden_curve=((0.0, 0.0), (10.0, 1.0)),
    )
    condition = profile.at_age(5.0)
    assert condition is not None
    assert condition.parameters.presynaptic_gain == 0.75
    assert condition.parameters.noise_std == 0.1


def test_profile_without_evidence_curve_is_unavailable() -> None:
    profile = DiseaseProfile(condition_id="waiting", gene_model="PINK1", seed=0)
    assert profile.burden_at(5.0) is None
    assert profile.at_age(5.0) is None
