from joi_companion.core.virtual_qubit_stability import VirtualQubitStability, VirtualQubitConfig

def test_normalize_and_recover():
    vq = VirtualQubitStability(VirtualQubitConfig(max_states_in_memory=4, paging_enabled=False))
    st = vq.set_state("a", [3.0, 4.0])
    assert abs(sum(x*x for x in st.amplitudes) - 1.0) < 1e-6

def test_paging_offload(tmp_path):
    cfg = VirtualQubitConfig(
        max_states_in_memory=2,
        paging_enabled=True,
        offload_dir=str(tmp_path),
    )
    vq = VirtualQubitStability(cfg)
    vq.set_state("k1", [1,0])
    vq.set_state("k2", [0,1])
    vq.set_state("k3", [0.6,0.8])  # should force page-out
    assert len(vq.snapshot()) <= 2
    s = vq.get_state("k1") or vq.get_state("k2") or vq.get_state("k3")
    assert s is not None
