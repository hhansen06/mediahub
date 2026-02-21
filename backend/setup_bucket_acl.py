#!/usr/bin/env python3
"""
Script to set the S3 bucket ACL to public-read.
Run this once to configure the bucket for public access.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.s3_service import s3_service

if __name__ == "__main__":
    print("Setting S3 bucket ACL to public-read...")
    success = s3_service.set_bucket_public_read_acl()
    
    if success:
        print("✓ Bucket is now publicly readable!")
        print("  Images can be accessed directly via their S3 URLs without presigned tokens.")
        sys.exit(0)
    else:
        print("✗ Failed to set bucket ACL. Check your S3 credentials and permissions.")
        sys.exit(1)
