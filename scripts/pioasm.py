Import("env")
import os
import subprocess

def find_pio_files(source_dir):
    """Find all .pio files in the source directory and subdirectories."""
    pio_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.pio'):
                pio_files.append(os.path.join(root, file))
    return pio_files

def run_pioasm(pio_file, output_file):
    """Run pioasm to convert .pio file to .h header file."""
    cmd = [
        env.get("PIOASM", "pioasm"),
        "-o", "c-sdk",
        pio_file,
        output_file
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running pioasm: {result.stderr}")
        env.Exit(1)
    else:
        print(f"Generated: {output_file}")

def pioasm_pre_build(source, target, env):
    """Pre-build hook to process all .pio files."""
    project_dir = env.get("PROJECT_DIR")
    src_dir = os.path.join(project_dir, "src")
    lib_dir = os.path.join(project_dir, "lib")
    
    # Find .pio files in src and lib directories
    pio_files = []
    if os.path.exists(src_dir):
        pio_files.extend(find_pio_files(src_dir))
    if os.path.exists(lib_dir):
        pio_files.extend(find_pio_files(lib_dir))
    
    for pio_file in pio_files:
        # Generate output filename: replace .pio with .pio.h
        output_file = pio_file.replace('.pio', '.pio.h')
        
        # Check if output file needs to be regenerated
        if not os.path.exists(output_file) or os.path.getmtime(pio_file) > os.path.getmtime(output_file):
            run_pioasm(pio_file, output_file)

# Register the pre-build hook
env.AddPreAction("buildprog", pioasm_pre_build)