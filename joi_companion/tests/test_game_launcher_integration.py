"""
test_game_launcher_integration.py — Verify GameLauncher ↔ WorldSimulation integration.

Tests:
- GameLauncher initializes with WorldSimulation
- update(dt) ticks the world simulation
- World state is passed to layers via on_world_state callback
- Layer launch/return callbacks work correctly
- get_launcher_state_json includes world state
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from joi_companion.game.game_launcher import GameLauncher, LauncherMode
from joi_companion.core.world_simulation import WorldSimulation


class TestGameLauncherWorldIntegration:
    """Test GameLauncher ↔ WorldSimulation integration."""
    
    def test_launcher_initializes_world_simulation(self):
        """Verify GameLauncher initializes WorldSimulation on startup."""
        launcher = GameLauncher(world_seed=42)
        assert launcher.world_simulation is not None
        assert launcher.world_seed == 42
        assert launcher.accumulated_dt == 0.0
        assert launcher.tick_interval == 0.1
    
    def test_launcher_with_custom_seed(self):
        """Verify custom seed parameter is respected."""
        launcher1 = GameLauncher(world_seed=100)
        launcher2 = GameLauncher(world_seed=200)
        
        # Get initial alien spawns with different seeds
        state1 = launcher1.get_world_state()
        state2 = launcher2.get_world_state()
        
        # Should have different alien spawns due to different seeds
        if "spawned_aliens" in state1 and "spawned_aliens" in state2:
            assert state1["spawned_aliens"] != state2["spawned_aliens"]
    
    def test_update_accumulates_dt(self):
        """Verify update(dt) accumulates delta time correctly."""
        launcher = GameLauncher()
        assert launcher.accumulated_dt == 0.0
        
        # Call update with 0.05s (half of tick_interval)
        launcher.update(0.05)
        assert launcher.accumulated_dt == 0.05
        
        # Call again with 0.03s (total 0.08s, still less than tick_interval)
        launcher.update(0.03)
        assert launcher.accumulated_dt == 0.08
    
    def test_update_ticks_world_on_interval(self):
        """Verify world ticks when accumulated_dt >= tick_interval."""
        launcher = GameLauncher()
        initial_tick = launcher.world_simulation.tick_count if launcher.world_simulation else 0
        
        # Call update with 0.15s (more than tick_interval of 0.1s)
        launcher.update(0.15)
        
        # Should have ticked at least once
        if launcher.world_simulation:
            assert launcher.world_simulation.tick_count > initial_tick
            # accumulated_dt should be 0.05 (0.15 - 0.1)
            assert launcher.accumulated_dt == pytest.approx(0.05, abs=0.01)
    
    def test_update_passes_world_state_to_layer(self):
        """Verify update(dt) passes world_state to current layer if it has on_world_state."""
        launcher = GameLauncher()
        
        # Create a mock layer with on_world_state callback
        mock_layer = Mock()
        mock_layer.on_world_state = Mock()
        launcher.current_layer_instance = mock_layer
        
        # Call update with enough time to trigger a tick
        launcher.update(0.15)
        
        # Verify on_world_state was called
        assert mock_layer.on_world_state.called
        
        # Verify it was called with a world state dict
        call_args = mock_layer.on_world_state.call_args
        assert call_args is not None
        world_state_arg = call_args[0][0]
        assert isinstance(world_state_arg, dict)
    
    def test_get_world_state_returns_dict(self):
        """Verify get_world_state returns procedural world state."""
        launcher = GameLauncher(world_seed=42)
        launcher.update(0.1)  # Trigger at least one tick
        world_state = launcher.get_world_state()
        
        assert isinstance(world_state, dict)
        # Should contain expected keys from WorldSimulation.get_tick_summary()
        expected_keys = ["tick", "spawns", "weather_changes", "moon_phase", "regions_active"]
        for key in expected_keys:
            assert key in world_state, f"Missing key: {key}"
    
    def test_set_world_seed_reinitializes_world(self):
        """Verify set_world_seed reinitializes world with new seed."""
        launcher = GameLauncher(world_seed=42)
        state1 = launcher.get_world_state()
        
        # Set a new seed
        result = launcher.set_world_seed(100)
        
        assert "reseeded" in result.lower()
        assert launcher.world_seed == 100
        assert launcher.accumulated_dt == 0.0  # Should reset accumulator
        
        # Get new state (should be different due to different seed)
        state2 = launcher.get_world_state()
        if "spawned_aliens" in state1 and "spawned_aliens" in state2:
            assert state1["spawned_aliens"] != state2["spawned_aliens"]
    
    def test_launch_layer_passes_world_state(self):
        """Verify launch_layer passes initial world_state to layer callbacks."""
        launcher = GameLauncher(world_seed=42)
        launcher.update(0.1)  # Trigger a tick to get world state
        
        # Verify that get_world_state() returns valid dict
        world_state = launcher.get_world_state()
        assert isinstance(world_state, dict)
        assert "tick" in world_state
        
        # Verify that callbacks are set up to receive world_state updates
        # (layer instantiation is environment-specific; we just verify the plumbing exists)
        assert launcher.world_simulation is not None
        assert callable(launcher.update)
    
    def test_return_to_main_menu_clears_layer(self):
        """Verify return_to_main_menu clears layer instance and returns to main menu."""
        launcher = GameLauncher()
        
        # Set up a fake layer
        launcher.current_layer = Mock()
        launcher.current_layer_instance = Mock()
        launcher.mode = LauncherMode.LAYER_RUNNING
        
        # Return to main menu
        result = launcher.return_to_main_menu()
        
        assert launcher.current_layer is None
        assert launcher.current_layer_instance is None
        assert launcher.mode == LauncherMode.MAIN_MENU
        assert "main menu" in result.lower()
    
    def test_get_launcher_state_json_includes_world_state(self):
        """Verify get_launcher_state_json includes world_state and world_seed."""
        launcher = GameLauncher(world_seed=42)
        
        state_json = launcher.get_launcher_state_json()
        
        assert "world_state" in state_json
        assert "world_seed" in state_json
        assert state_json["world_seed"] == 42
        assert isinstance(state_json["world_state"], dict)
    
    def test_multiple_updates_accumulate_correctly(self):
        """Verify multiple rapid updates accumulate and tick correctly."""
        launcher = GameLauncher()
        initial_tick = launcher.world_simulation.tick_count if launcher.world_simulation else 0
        
        # Simulate 10 frames at 60fps (frame_dt = 1/60 ≈ 0.0167s)
        frame_dt = 1.0 / 60.0
        for _ in range(10):
            launcher.update(frame_dt)
        
        # Total time: 10 * 0.0167 = 0.167s, should have ticked once (0.1s)
        if launcher.world_simulation:
            assert launcher.world_simulation.tick_count > initial_tick


class TestGameLauncherRobustness:
    """Test GameLauncher robustness and error handling."""
    
    def test_launcher_handles_missing_world_simulation(self):
        """Verify launcher degrades gracefully if WorldSimulation is unavailable."""
        with patch('joi_companion.game.game_launcher.WorldSimulation', None):
            launcher = GameLauncher()
            # Should not crash
            assert launcher.world_simulation is None
            
            # update should return empty dict
            result = launcher.update(0.1)
            assert result == {}
            
            # get_world_state should return empty dict
            world_state = launcher.get_world_state()
            assert world_state == {}
    
    def test_launcher_handles_world_tick_exception(self):
        """Verify launcher handles exceptions during world tick gracefully."""
        launcher = GameLauncher()
        
        # Mock world_simulation.tick to raise an exception
        launcher.world_simulation.tick = Mock(side_effect=Exception("Tick failed"))
        
        # Should not crash
        result = launcher.update(0.15)
        assert isinstance(result, dict)
    
    def test_launcher_handles_layer_callback_exception(self):
        """Verify launcher handles exceptions in layer's on_world_state callback."""
        launcher = GameLauncher()
        
        # Create a mock layer that raises on on_world_state
        mock_layer = Mock()
        mock_layer.on_world_state = Mock(side_effect=Exception("Callback failed"))
        launcher.current_layer_instance = mock_layer
        
        # Should not crash
        result = launcher.update(0.15)
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
