# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Connection management for AWS services used by Amazon RDS Management MCP Server."""

import boto3
import os
from botocore.config import Config
from typing import Any, Optional


class BaseConnectionManager:
    """Base class for AWS service connection managers."""

    _client: Optional[Any] = None
    _service_name: str = '' 
    _env_prefix: str = ''  

    @classmethod
    def get_connection(cls) -> Any:
        """Get or create an AWS service client connection with retry capabilities.

        Returns:
            boto3.client: An AWS service client configured with retries
        """
        if cls._client is None:
            # get AWS configuration from environment
            aws_profile = os.environ.get('AWS_PROFILE', '')
            aws_region = os.environ.get('AWS_REGION', 'us-east-1')
            aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

            # configuration retry settings
            max_retries = int(os.environ.get(f'{cls._env_prefix}_MAX_RETRIES', '3'))
            retry_mode = os.environ.get(f'{cls._env_prefix}_RETRY_MODE', 'standard')
            connect_timeout = int(os.environ.get(f'{cls._env_prefix}_CONNECT_TIMEOUT', '5'))
            read_timeout = int(os.environ.get(f'{cls._env_prefix}_READ_TIMEOUT', '10'))

            # create boto3 config with retry settings
            config = Config(
                retries={'max_attempts': max_retries, 'mode': retry_mode},
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                # configuration custom user agent to identify requests from LLM/MCP
                user_agent_extra='MCP/AmazonRDSManagementMCPServer',
            )

            # init AWS client with session and config
            # if user changes credential, it will be reflected immediately in the next call
            if aws_profile and aws_profile != '':
                session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
            else:
                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token,
                    region_name=aws_region
                )
            cls._client = session.client(service_name=cls._service_name, config=config)

        return cls._client

    @classmethod
    def close_connection(cls) -> None:
        """Close the AWS service client connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None


class RDSConnectionManager(BaseConnectionManager):
    """Manages connection to RDS using boto3."""

    _client: Optional[Any] = None
    _service_name = 'rds'
    _env_prefix = 'RDS'
    _readonly = True
    _region = None
    
    @classmethod
    def initialize(cls, readonly: bool = True, region: str = None):
        """Initialize the connection manager with readonly flag and region.
        
        Args:
            readonly (bool): Whether to run in readonly mode
            region (str): AWS region for RDS operations
        """
        cls._readonly = readonly
        cls._region = region or os.environ.get('AWS_REGION', 'us-east-1')
        
        cls._client = None
    
    @classmethod
    def is_readonly(cls) -> bool:
        """Check if the server is running in readonly mode.
        
        Returns:
            bool: True if readonly mode is enabled, False otherwise
        """
        return cls._readonly
    
    @classmethod
    def get_region(cls) -> str:
        """Get the AWS region.
        
        Returns:
            str: AWS region
        """
        return cls._region


class PIConnectionManager(BaseConnectionManager):
    """Manages connection to PI using boto3."""

    _client: Optional[Any] = None
    _service_name = 'pi'
    _env_prefix = 'PI'
