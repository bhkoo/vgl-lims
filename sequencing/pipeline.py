import os
import subprocess
import glob
import logging
from pathlib import Path
from datetime import datetime
import gzip

logger = logging.getLogger(__name__)


class PacBioProcessor:
    """
    Process PacBio sequencing data:
    1. Find BAM file in given path
    2. Convert to FASTQ.gz
    3. Generate rdeval snapshot
    4. Upload to S3
    5. Calculate total bases and coverage
    """
    
    def __init__(self, run, s3_bucket='your-bucket-name'):
        self.run = run
        self.s3_bucket = s3_bucket
        self.log = []
    
    def log_step(self, message):
        """Add timestamped log entry"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.log.append(log_entry)
        logger.info(log_entry)
    
    def find_bam_file(self):
        """Find BAM file in the HPC filepath"""
        bam_filepath = os.path.join(self.run.hpc_filepath, 'hifi_reads', 
                                    "{self.run.metadata_id}.hifi_reads.{self.run.barcode}.bam")
        self.log_step(f"Finding BAM file: {bam_filepath}")
        
        if not os.path.exists(bam_filepath):
            raise FileNotFoundError(f"No BAM files found in {self.run.hpc_filepath}")
        
        self.run.bam_filepath = bam_filepath
        return bam_filepath
    
    def bam_to_fastq(self, bam_file):
        """Convert BAM to FASTQ.gz using samtools or bam2fastq"""
        output_dir = os.path.join(os.path.dirname(bam_file), 'fastq_output')
        os.makedirs(output_dir, exist_ok=True)

        fastq_file = bam_file.replace('bam', '.fastq.gz')
        fastq_path = os.path.join(output_dir, fastq_file)
        
        self.log_step(f"Converting BAM to FASTQ.gz: {fastq_path}")
        
        # Using samtools (adjust command based on your preference)
        try:
            cmd = [
                'samtools', 'fastq',
                '-@', '4',  # threads
                bam_file, '>', fastq_file
            ]
            
            # Pipe through gzip
            with gzip.open(fastq_path, 'wt') as f_out:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                for line in process.stdout:
                    f_out.write(line)
                
                returncode = process.wait()
                
                if returncode != 0:
                    stderr = process.stderr.read()
                    raise subprocess.CalledProcessError(returncode, cmd, stderr=stderr)
            
            self.log_step(f"Successfully created FASTQ.gz: {fastq_path}")
            self.run.fastq_filepath = fastq_path
            return fastq_path
            
        except subprocess.CalledProcessError as e:
            self.log_step(f"ERROR converting BAM to FASTQ: {e}")
            raise
        except FileNotFoundError:
            self.log_step("ERROR: samtools not found. Please install samtools.")
            raise
    
    def generate_rdeval_snapshot(self, fastq_path):
        """Run your rdeval script to generate snapshot"""
        self.log_step(f"Generating rdeval snapshot for: {fastq_path}")
        
        # Adjust this to match your rdeval command
        # Example: rdeval snapshot input.fastq.gz -o output.rdeval
        snapshot_path = fastq_path + ".rd"
        
        try:
            cmd = [
                'rdeval',
                fastq_path,
                '-j',
                '8',
                '-o', snapshot_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=True
            )
            
            self.log_step(f"Successfully generated rdeval snapshot: {snapshot_path}")
            return snapshot_path
            
        except subprocess.CalledProcessError as e:
            self.log_step(f"ERROR generating rdeval snapshot: {e.stderr}")
            raise
        except FileNotFoundError:
            self.log_step("ERROR: rdeval not found. Please install rdeval or update path.")
            raise
    
    def upload_to_s3(self, path):
        """Upload file to S3"""
        s3_key = f"species/{self.run.individual.species}/{self.run.individual.species}/{os.path.basename(path)}"
        s3_path = f"s3://{self.s3_bucket}/{s3_key}"
        
        self.log_step(f"Uploading to S3: {s3_path}")
        
        try:
            cmd = [
                'aws', 's3', 'cp',
                path,
                s3_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                check=True
            )
            
            self.log_step(f"Successfully uploaded to S3: {s3_path}")
            self.run.rdeval_s3_path = s3_path
            return s3_path
            
        except subprocess.CalledProcessError as e:
            self.log_step(f"ERROR uploading to S3: {e.stderr}")
            raise
    
    def calculate_total_bases(self, fastq_path):
        """Calculate total basepairs in FASTQ.gz file"""
        self.log_step(f"Calculating total bases in: {fastq_path}")
        
        total_bases = 0
        
        try:
            with gzip.open(fastq_path, 'rt') as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    # Every 4 lines is one read; line 2 is the sequence
                    if line_num % 4 == 2:
                        total_bases += len(line.strip())
            
            self.log_step(f"Total bases: {total_bases:,} bp")
            self.run.total_bases = total_bases
            return total_bases
            
        except Exception as e:
            self.log_step(f"ERROR calculating total bases: {e}")
            raise
    
    def calculate_coverage(self):
        """Calculate coverage based on total bases and expected genome size"""
        if not self.run.total_bases:
            self.log_step("Cannot calculate coverage: total_bases not set")
            return None
        
        expected_size = self.run.individual.expected_genome_size_bp
        
        if not expected_size:
            self.log_step("Cannot calculate coverage: expected_genome_size_bp not set for individual")
            return None
        
        coverage = self.run.total_bases / expected_size
        self.log_step(f"Calculated coverage: {coverage:.2f}x")
        
        self.run.coverage = coverage
        return coverage
    
    def process(self):
        """Run the complete processing pipeline"""
        try:
            self.log_step(f"Starting processing for run: {self.run.run_id}")
            self.run.status = 'processing'
            self.run.save()
            
            # Step 1: Find BAM file
            bam_path = self.find_bam_file()
            
            # Step 2: Convert to FASTQ.gz
            fastq_path = self.bam_to_fastq(bam_path)
            
            # Step 3: Calculate total bases
            self.calculate_total_bases(fastq_path)
            
            # Step 4: Calculate coverage
            self.calculate_coverage()
            
            # Step 5: Generate rdeval snapshot
            rdeval_path = self.generate_rdeval_snapshot(fastq_path)
            
            # Step 6: Upload to S3
            self.upload_to_s3(bam_path)
            self.upload_to_s3(fastq_path)
            self.upload_to_s3(rdeval_path)
            
            # Mark as complete
            self.run.status = 'complete'
            self.run.processing_log = '\n'.join(self.log)
            self.run.save()
            
            self.log_step("Processing completed successfully!")
            return True
            
        except Exception as e:
            self.log_step(f"FATAL ERROR: {str(e)}")
            self.run.status = 'error'
            self.run.processing_log = '\n'.join(self.log)
            self.run.save()
            logger.exception(f"Error processing run {self.run.run_id}")
            return False


def process_pacbio_run(run_id, s3_bucket='your-bucket-name'):
    """
    Process a PacBio run by ID.
    Can be called from views or as a background task.
    """
    from .models import PacBioRun
    
    try:
        run = PacBioRun.objects.get(run_id=run_id)
        processor = PacBioProcessor(run, s3_bucket=s3_bucket)
        return processor.process()
    except PacBioRun.DoesNotExist:
        logger.error(f"PacBio run not found: {run_id}")
        return False