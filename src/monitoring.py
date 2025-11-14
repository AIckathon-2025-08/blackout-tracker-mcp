"""
Automatic monitoring setup for electricity outages.

This module handles automatic setup of background monitoring
when the user enables notifications through configure_monitoring.
"""
import os
import sys
import platform
import subprocess
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_python_path() -> str:
    """Get the path to the Python interpreter."""
    return sys.executable


def setup_cron_monitoring(check_interval_minutes: int) -> tuple[bool, str]:
    """
    Set up cron job for automatic monitoring (macOS/Linux).

    Args:
        check_interval_minutes: How often to check in minutes

    Returns:
        (success, message)
    """
    project_root = get_project_root()
    python_path = get_python_path()
    monitor_script = project_root / "monitor_outages.py"

    # Create cron expression (every N minutes)
    cron_expr = f"*/{check_interval_minutes} * * * *"

    # Cron job command
    log_path = Path.home() / "outage_monitor.log"
    cron_command = (
        f"{cron_expr} cd {project_root} && "
        f"{python_path} {monitor_script} >> {log_path} 2>&1"
    )

    try:
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )

        current_crontab = result.stdout if result.returncode == 0 else ""

        # Remove any existing outage monitor jobs
        lines = [
            line for line in current_crontab.split('\n')
            if 'monitor_outages.py' not in line and line.strip()
        ]

        # Add new job
        lines.append(cron_command)
        lines.append("")  # Empty line at end

        new_crontab = '\n'.join(lines)

        # Install new crontab
        proc = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=new_crontab)

        if proc.returncode == 0:
            return True, f"✓ Cron job installed. Checking every {check_interval_minutes} minutes.\nLogs: {log_path}"
        else:
            return False, f"Failed to install cron job: {stderr}"

    except FileNotFoundError:
        return False, "Cron not available on this system."
    except Exception as e:
        return False, f"Error setting up cron: {str(e)}"


def remove_cron_monitoring() -> tuple[bool, str]:
    """
    Remove cron job for automatic monitoring.

    Returns:
        (success, message)
    """
    try:
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return True, "No cron jobs to remove."

        current_crontab = result.stdout

        # Remove outage monitor jobs
        lines = [
            line for line in current_crontab.split('\n')
            if 'monitor_outages.py' not in line and line.strip()
        ]

        if len(lines) == len([l for l in current_crontab.split('\n') if l.strip()]):
            return True, "No outage monitor cron job found."

        lines.append("")  # Empty line at end
        new_crontab = '\n'.join(lines)

        # Install new crontab (without our job)
        proc = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=new_crontab)

        if proc.returncode == 0:
            return True, "✓ Automatic monitoring disabled. Cron job removed."
        else:
            return False, f"Failed to remove cron job: {stderr}"

    except FileNotFoundError:
        return False, "Cron not available on this system."
    except Exception as e:
        return False, f"Error removing cron: {str(e)}"


def setup_launchd_monitoring(check_interval_minutes: int) -> tuple[bool, str]:
    """
    Set up LaunchAgent for automatic monitoring (macOS).

    Args:
        check_interval_minutes: How often to check in minutes

    Returns:
        (success, message)
    """
    project_root = get_project_root()
    python_path = get_python_path()
    monitor_script = project_root / "monitor_outages.py"

    # LaunchAgent plist path
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents_dir / "com.blackout.monitor.plist"

    # Create plist content
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.blackout.monitor</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{monitor_script}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{project_root}</string>

    <key>StartInterval</key>
    <integer>{check_interval_minutes * 60}</integer>

    <key>StandardOutPath</key>
    <string>/tmp/outage_monitor.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/outage_monitor.error.log</string>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""

    try:
        # Write plist file
        with open(plist_path, 'w') as f:
            f.write(plist_content)

        # Unload old service if exists (ignore errors)
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True
        )

        # Load new service
        result = subprocess.run(
            ["launchctl", "load", str(plist_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return True, f"✓ LaunchAgent installed. Checking every {check_interval_minutes} minutes.\nLogs: /tmp/outage_monitor.log"
        else:
            # Fallback to cron if LaunchAgent fails
            logger.warning(f"LaunchAgent failed: {result.stderr}. Falling back to cron.")
            return setup_cron_monitoring(check_interval_minutes)

    except Exception as e:
        logger.warning(f"LaunchAgent setup failed: {e}. Falling back to cron.")
        return setup_cron_monitoring(check_interval_minutes)


def remove_launchd_monitoring() -> tuple[bool, str]:
    """
    Remove LaunchAgent for automatic monitoring (macOS).

    Returns:
        (success, message)
    """
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.blackout.monitor.plist"

    try:
        if plist_path.exists():
            # Unload service
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                capture_output=True
            )

            # Remove plist file
            plist_path.unlink()

            return True, "✓ Automatic monitoring disabled. LaunchAgent removed."
        else:
            # Try removing cron as fallback
            return remove_cron_monitoring()

    except Exception as e:
        logger.warning(f"LaunchAgent removal failed: {e}. Trying cron.")
        return remove_cron_monitoring()


def is_running_in_docker() -> bool:
    """Check if we're running inside a Docker container."""
    # Check for .dockerenv file
    if os.path.exists('/.dockerenv'):
        return True

    # Check for docker in cgroup
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        pass

    return False


def setup_monitoring(check_interval_minutes: int) -> tuple[bool, str]:
    """
    Set up automatic monitoring based on platform.

    Args:
        check_interval_minutes: How often to check in minutes

    Returns:
        (success, message)
    """
    # Check if running in Docker
    if is_running_in_docker():
        logger.info("Detected Docker environment - notification daemon should handle monitoring")
        return True, (
            "✓ Configuration saved!\n\n"
            "🐳 Running in Docker: The notification-daemon container will automatically\n"
            "   check for upcoming outages and send notifications.\n\n"
            f"📋 Settings:\n"
            f"  • Check interval: every {check_interval_minutes} minutes\n"
            f"  • Notify: {check_interval_minutes} minutes before outages\n\n"
            "💡 The daemon runs in the background and shares your configuration."
        )

    system = platform.system()

    logger.info(f"Setting up monitoring on {system}")

    if system == "Darwin":  # macOS
        # Try LaunchAgent first, fallback to cron
        success, message = setup_launchd_monitoring(check_interval_minutes)
        if success:
            return success, message
        # Fallback to cron if LaunchAgent fails
        return setup_cron_monitoring(check_interval_minutes)

    elif system == "Linux":
        # Use cron on Linux
        return setup_cron_monitoring(check_interval_minutes)

    elif system == "Windows":
        # Windows not supported yet - provide manual instructions
        return False, (
            "⚠️ Automatic setup not available on Windows.\n\n"
            "Please set up Task Scheduler manually:\n"
            f"1. Open Task Scheduler\n"
            f"2. Create task: Run every {check_interval_minutes} minutes\n"
            f"3. Action: {get_python_path()} {get_project_root() / 'monitor_outages.py'}\n\n"
            "Or use Docker for automatic monitoring."
        )
    else:
        return False, f"Automatic setup not supported on {system}."


def remove_monitoring() -> tuple[bool, str]:
    """
    Remove automatic monitoring based on platform.

    Returns:
        (success, message)
    """
    # Check if running in Docker
    if is_running_in_docker():
        logger.info("Detected Docker environment - notification daemon will stop monitoring")
        return True, (
            "✓ Notifications disabled!\n\n"
            "🐳 Running in Docker: The notification-daemon container will stop\n"
            "   checking for outages. You can re-enable anytime."
        )

    system = platform.system()

    logger.info(f"Removing monitoring on {system}")

    if system == "Darwin":  # macOS
        # Try LaunchAgent first
        success, message = remove_launchd_monitoring()
        if success and "LaunchAgent" in message:
            return success, message
        # Also try cron as fallback
        return remove_cron_monitoring()

    elif system == "Linux":
        return remove_cron_monitoring()

    elif system == "Windows":
        return False, "Please remove Task Scheduler entry manually."
    else:
        return False, f"Automatic removal not supported on {system}."


def check_monitoring_status() -> tuple[bool, str]:
    """
    Check if automatic monitoring is currently active.

    Returns:
        (is_active, details)
    """
    system = platform.system()

    # Check LaunchAgent (macOS)
    if system == "Darwin":
        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.blackout.monitor.plist"
        if plist_path.exists():
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True
            )
            if "com.blackout.monitor" in result.stdout:
                return True, "LaunchAgent active"

    # Check cron (macOS/Linux)
    if system in ["Darwin", "Linux"]:
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and "monitor_outages.py" in result.stdout:
                return True, "Cron job active"
        except:
            pass

    return False, "Not active"
