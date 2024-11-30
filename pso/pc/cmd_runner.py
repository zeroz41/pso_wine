import os
import select
import pty
import errno
import time
import signal
import subprocess
from contextlib import contextmanager

#utility base class for running cmds.
#zeroz/tj

class ProcessTimeoutError(Exception):
    pass

class CommandRunner:
    @contextmanager
    def process_timeout(self, seconds):
        def handle_timeout(signum, frame):
            raise ProcessTimeoutError(f"Process timed out after {seconds} seconds")
        
        signal.signal(signal.SIGALRM, handle_timeout)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            
    def run_command(self, command, timeout=60, env=None, capture_output=False):
        print(f"Debug - Running command: {command}")
        output_buffer = []

        def kill_process_tree(pid):
            try:
                parent = subprocess.Popen(['ps', '-o', 'pid', '--ppid', str(pid), '--noheaders'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, _ = parent.communicate()
                for child_pid in out.split():
                    if child_pid:
                        try:
                            os.kill(int(child_pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            except Exception as e:
                print(f"Error killing process tree: {e}")

        master_fd, slave_fd = pty.openpty()
        process = None
        try:
            process = subprocess.Popen(
                command,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=env,
                preexec_fn=os.setsid
            )
            os.close(slave_fd)
            
            start_time = time.time()
            while True:
                if timeout is not None and time.time() - start_time > timeout:
                    print(f"Command timed out after {timeout} seconds")
                    if process:
                        kill_process_tree(process.pid)
                    return (1, '') if capture_output else 1
                    
                try:
                    ready, _, _ = select.select([master_fd], [], [], 1.0)
                    if ready:
                        try:
                            data = os.read(master_fd, 1024).decode('utf-8', 'ignore')
                            if not data:
                                break
                            if capture_output:
                                output_buffer.append(data)
                            if not capture_output:  # Only print if not capturing
                                print(data, end='', flush=True)
                        except OSError as e:
                            if e.errno != errno.EIO:
                                raise
                            break
                    elif process.poll() is not None:
                        break
                except (select.error, OSError) as e:
                    if process.poll() is not None:
                        break
                    print(f"Error during command execution: {e}")
                    break

            if process.poll() is None:
                kill_process_tree(process.pid)
                return (1, '') if capture_output else 1
                
            if capture_output:
                return process.returncode if process.returncode is not None else 1, ''.join(output_buffer)
            return process.returncode if process.returncode is not None else 1
            
        except Exception as e:
            print(f"Error during command execution: {e}")
            if process:
                kill_process_tree(process.pid)
            return (1, '') if capture_output else 1
        finally:
            os.close(master_fd)