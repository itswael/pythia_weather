# Technical Design Document (TDD)
# Pythia Weather Data Retrieval System

## Document Information
- **Document Version**: 1.0
- **Date**: October 14, 2025
- **Project**: Pythia Weather Data Retrieval System
- **Author**: System Architecture Team

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Architecture Design](#2-architecture-design)
3. [Component Specifications](#3-component-specifications)
4. [Data Flow Design](#4-data-flow-design)
5. [Interface Design](#5-interface-design)
6. [Database Design](#6-database-design)
7. [Security Design](#7-security-design)
8. [Performance Design](#8-performance-design)
9. [Error Handling Design](#9-error-handling-design)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Testing Strategy](#11-testing-strategy)
12. [Monitoring and Logging](#12-monitoring-and-logging)

---

## 1. System Overview

### 1.1 Purpose
The Pythia Weather Data Retrieval System is designed to provide automated, reliable access to meteorological data from NASA POWER (Prediction of Worldwide Energy Resources) databases for agricultural and research applications.

### 1.2 Scope
- Fetch daily meteorological data from multiple NASA POWER sources
- Convert data to ICASA (International Consortium for Agricultural Systems Applications) format
- Provide intelligent fallback mechanisms between data sources
- Support both real-time and historical data retrieval

### 1.3 System Goals
- **Reliability**: 99.5% uptime with automatic failover
- **Performance**: Sub-30 second response times for typical requests
- **Scalability**: Support for concurrent requests and batch processing
- **Data Integrity**: Validation and consistency checks for all retrieved data

### 1.4 System Constraints
- Limited to NASA POWER geographic coverage
- Daily temporal resolution only
- Dependent on external NASA infrastructure availability
- Network connectivity required for all operations

---

## 2. Architecture Design

### 2.1 System Architecture Pattern
**Microservices Architecture** with modular, loosely-coupled components implementing a **Service-Oriented Architecture (SOA)** pattern.

### 2.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Main Orchestrator                           │
│                  (weather.py)                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Request Validation & Routing Logic           │   │
│  │     ┌─────────────────┬─────────────────────────┐   │   │
│  │     │  Date-Based     │    Source Selection     │   │   │
│  │     │  Logic Engine   │       Logic             │   │   │
│  │     └─────────────────┴─────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────┬───────────────────────────┬───────────────────┘
              │                           │
              ▼                           ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│    API Data Source      │    │    S3/Zarr Data Source  │
│  (weather_via_API.py)   │    │  (weather_via_S3.py)    │
│  ┌─────────────────────┐│    │  ┌─────────────────────┐│
│  │   HTTP Client       ││    │  │  Zarr Data Reader   ││
│  │   Management        ││    │  │     Manager         ││
│  └─────────────────────┘│    │  └─────────────────────┘│
│  ┌─────────────────────┐│    │  ┌─────────────────────┐│
│  │   Rate Limiting     ││    │  │  S3 Connection      ││
│  │   & Retry Logic     ││    │  │    Management       ││
│  └─────────────────────┘│    │  └─────────────────────┘│
└─────────────┬───────────┘    └─────────────┬───────────┘
              │                              │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌─────────────────────────────────┐
              │       Utility Layer             │
              │      (weather_util.py)          │
              │  ┌─────────────────────────────┐ │
              │  │   Data Format Converter     │ │
              │  │   (NASA → ICASA)            │ │
              │  └─────────────────────────────┘ │
              │  ┌─────────────────────────────┐ │
              │  │   Elevation Data Service    │ │
              │  │   (WELEV Integration)       │ │
              │  └─────────────────────────────┘ │
              │  ┌─────────────────────────────┐ │
              │  │   File I/O Operations       │ │
              │  └─────────────────────────────┘ │
              └─────────────────────────────────┘
                             │
                             ▼
              ┌─────────────────────────────────┐
              │      Configuration Layer        │
              │         (config.py)             │
              │  ┌─────────────────────────────┐ │
              │  │    API Endpoints            │ │
              │  │    Variable Mappings        │ │
              │  │    System Constants         │ │
              │  └─────────────────────────────┘ │
              └─────────────────────────────────┘
```

### 2.3 Component Interaction Flow

```
┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ Client  │───▶│ Orchestrator │───▶│ Source      │───▶│ Data         │
│ Request │    │ (Routing)    │    │ Selection   │    │ Retrieval    │
└─────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                           │                  │
                                           ▼                  │
                               ┌─────────────────┐            │
                               │ Fallback Logic  │            │
                               │ (if primary     │            │
                               │  source fails)  │            │
                               └─────────────────┘            │
                                           │                  │
                                           ▼                  ▼
                               ┌─────────────────┐    ┌──────────────┐
                               │ Alternative     │    │ Format       │
                               │ Data Source     │    │ Conversion   │
                               └─────────────────┘    │ (NASA→ICASA) │
                                           │          └──────────────┘
                                           │                  │
                                           ▼                  ▼
                               ┌─────────────────┐    ┌──────────────┐
                               │ Error Handling  │    │ File Output  │
                               │ & Reporting     │    │ Generation   │
                               └─────────────────┘    └──────────────┘
```

---

## 3. Component Specifications

### 3.1 Main Orchestrator (weather.py)

#### 3.1.1 Class: WeatherDataOrchestrator
```python
class WeatherDataOrchestrator:
    """Main coordination component for weather data retrieval."""
    
    def __init__(self):
        self.api_client = APIDataSource()
        self.s3_client = S3DataSource()
        self.validator = DataValidator()
        
    async def download_weather_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        include_srad: bool = True,
        include_met: bool = True,
        source: str = "S3"
    ) -> Optional[str]
```

#### 3.1.2 Key Responsibilities
- **Request Coordination**: Orchestrates the entire data retrieval workflow
- **Source Selection**: Implements intelligent source selection logic based on date recency
- **Fallback Management**: Handles primary source failures with automatic fallback
- **Validation**: Ensures data integrity and request parameter validation
- **File Management**: Coordinates output file generation and storage

#### 3.1.3 Decision Logic
```python
def _select_primary_source(self, end_date: date, preferred_source: str) -> str:
    """
    Decision matrix for source selection:
    - Recent data (≤7 days): API preferred
    - Historical data (>7 days): S3 preferred
    - User preference override available
    """
    days_old = (date.today() - end_date).days
    
    if days_old <= 7 and preferred_source != "S3":
        return "API"
    elif days_old > 7 and preferred_source != "API":
        return "S3"
    else:
        return preferred_source
```

### 3.2 API Data Source (weather_via_API.py)

#### 3.2.1 Class: APIDataSource
```python
class APIDataSource:
    """NASA POWER API client with enhanced error handling."""
    
    def __init__(self):
        self.base_url = NASA_POWER_API_BASE
        self.session_config = {
            'timeout': 60.0,
            'retries': 3,
            'backoff_factor': 1.0
        }
        
    async def get_Daily_API_WTH(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        include_srad: bool = True,
        include_met: bool = True
    ) -> str
```

#### 3.2.2 Technical Specifications
- **Protocol**: HTTPS/REST
- **Client Library**: httpx (async)
- **Timeout Configuration**: 60 seconds
- **Retry Strategy**: Exponential backoff with 3 attempts
- **Rate Limiting**: Built-in respect for NASA API limits
- **Error Handling**: Comprehensive HTTP status code handling

#### 3.2.3 Parameter Construction Logic
```python
def _build_parameters(self, include_srad: bool, include_met: bool) -> str:
    """
    Dynamically constructs parameter list based on requirements:
    - Solar: ALLSKY_SFC_SW_DWN
    - Meteorological: T2M_MAX, T2M_MIN, PRECTOTCORR
    """
    base_params = NASA_POWER_API_PARAMS.split(",")
    filtered_params = []
    
    if include_srad:
        filtered_params.extend([p for p in base_params if "ALLSKY" in p])
    if include_met:
        filtered_params.extend([p for p in base_params if "T2M" in p or "PREC" in p])
        
    return ",".join(filtered_params)
```

### 3.3 S3/Zarr Data Source (weather_via_S3.py)

#### 3.3.1 Class: S3DataSource
```python
class S3DataSource:
    """S3/Zarr data client for historical NASA POWER data."""
    
    def __init__(self):
        self.s3_filesystem = s3fs.S3FileSystem(anon=True)
        self.zarr_cache = {}
        self.discovery_cache = {}
        
    async def get_Daily_S3_WTH(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        include_srad: bool = True,
        include_met: bool = True
    ) -> str
```

#### 3.3.2 Data Source Management
```python
class ZarrDatasetManager:
    """Manages multiple Zarr dataset connections."""
    
    def __init__(self):
        self.syn1_dataset = None  # Solar radiation data
        self.merra2_dataset = None  # Meteorological data
        
    async def _resolve_zarr_urls(self) -> Dict[str, str]:
        """
        URL Resolution Strategy:
        1. Use provided URLs if available
        2. Attempt dynamic discovery via S3 listing
        3. Fallback to predefined hint URLs
        """
        return {
            'syn1': self._resolve_syn1_url(),
            'merra2': self._resolve_merra2_url()
        }
```

#### 3.3.3 Data Processing Pipeline
```python
async def _process_zarr_data(
    self,
    datasets: Dict[str, xr.Dataset],
    location: Tuple[float, float],
    date_range: Tuple[date, date]
) -> pd.DataFrame:
    """
    Multi-step processing pipeline:
    1. Spatial slicing (nearest neighbor for location)
    2. Temporal slicing (date range extraction)
    3. Variable extraction and renaming
    4. Unit conversions (W/m² → MJ/m²/day for solar)
    5. DataFrame merging and alignment
    """
```

### 3.4 Utility Layer (weather_util.py)

#### 3.4.1 Class: DataFormatConverter
```python
class DataFormatConverter:
    """Converts NASA POWER data to ICASA format."""
    
    def __init__(self):
        self.variable_mapping = variable_map
        self.elevation_service = ElevationService()
        
    def convert_to_wth_format(
        self,
        data_dict: Dict[str, Any],
        station_name: str = "S3PWR",
        elevation: Optional[float] = None
    ) -> str
```

#### 3.4.2 ICASA Format Specification
```python
class ICASAFormatSpec:
    """ICASA .wth file format specification."""
    
    HEADER_TEMPLATE = """*WEATHER DATA : NASA POWER via {source}

@ INSI      LAT     LONG  ELEV   TAV   AMP REFHT WNDHT
  {station:>4} {lat:8.3f} {long:8.3f} {elev:5.0f}  -99.0  -99.0  -99.0  -99.0

@  DATE{variables}"""
    
    DATE_FORMAT = "YYYYDDD"  # Year + Day of Year
    MISSING_VALUE = -99.0
    PRECISION = 1  # Decimal places for weather values
```

#### 3.4.3 Elevation Integration
```python
class ElevationService:
    """Handles elevation data lookup from WELEV dataset."""
    
    def __init__(self):
        self.welev_dataset = None
        self.cache = {}
        
    def get_elevation(self, lat: float, lon: float) -> float:
        """
        Elevation lookup with interpolation:
        1. Load WELEV NetCDF dataset
        2. Perform bilinear interpolation for exact coordinates
        3. Cache results for performance
        4. Handle missing data gracefully
        """
```

### 3.5 Configuration Management (config.py)

#### 3.5.1 Configuration Structure
```python
class SystemConfiguration:
    """Centralized configuration management."""
    
    # API Configuration
    NASA_POWER_API_BASE: str
    NASA_POWER_S3_BASE: str
    
    # Dataset URLs
    SYN1DAILY_ZARR_HINT: str
    MERRA2DAILY_ZARR_HINT: str
    
    # Variable Mappings
    VARIABLE_MAP: Dict[str, str]
    RENAME_MAPPINGS: Dict[str, Dict[str, str]]
    
    # System Parameters
    DATA_DIR: Path
    ELEVATION_FILE: Path
    DEFAULT_TIMEOUT: int = 60
    MAX_RETRIES: int = 3
```

---

## 4. Data Flow Design

### 4.1 Primary Data Flow

```
┌─────────────────┐
│ Client Request  │
│ (lat, lon,      │
│  date_range)    │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Input Validation│
│ & Sanitization  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Source Selection│
│ Logic           │
│ (API vs S3)     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│ Primary Source  │───▶│ Fallback Source │
│ Data Retrieval  │    │ (if failure)    │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
          ┌─────────────────┐
          │ Data Processing │
          │ & Validation    │
          └─────────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ Format          │
          │ Conversion      │
          │ (NASA → ICASA)  │
          └─────────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ Elevation       │
          │ Data Addition   │
          └─────────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ File Generation │
          │ & Storage       │
          └─────────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ Response        │
          │ (File Path)     │
          └─────────────────┘
```

### 4.2 Error Flow Design

```
┌─────────────────┐
│ Error Detected  │
│ (Network,       │
│  Data, Format)  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Error           │
│ Classification  │
│ & Logging       │
└─────────┬───────┘
          │
    ┌─────▼─────┐
    │Recoverable│
    │Error?     │
    └─────┬─────┘
          │
    ┌─────▼─────┐         ┌─────────────────┐
    │    Yes    │────────▶│ Retry Logic     │
    │           │         │ (Exponential    │
    └───────────┘         │  Backoff)       │
          │               └─────────┬───────┘
          │                         │
    ┌─────▼─────┐                   │
    │    No     │                   │
    │           │                   │
    └─────┬─────┘                   │
          │                         │
          ▼                         │
┌─────────────────┐                 │
│ Fallback Source │◀────────────────┘
│ Activation      │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Final Error     │
│ Handling &      │
│ User Notification│
└─────────────────┘
```

### 4.3 Caching Strategy

```python
class CacheManager:
    """Multi-level caching strategy."""
    
    def __init__(self):
        self.file_cache = {}      # Completed file cache
        self.dataset_cache = {}   # Zarr dataset cache
        self.elevation_cache = {} # Elevation lookup cache
        
    async def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """
        Cache hierarchy:
        1. Memory cache (fastest)
        2. File system cache (medium)
        3. Remote source (slowest)
        """
```

---

## 5. Interface Design

### 5.1 Public API Interface

#### 5.1.1 Primary Interface
```python
async def download_weather_data(
    latitude: float,           # [-90, 90]
    longitude: float,          # [-180, 180]
    start_date: date,          # ISO format
    end_date: date,            # ISO format
    include_srad: bool = True, # Include solar radiation
    include_met: bool = True,  # Include meteorological data
    source: str = "S3"         # "S3" or "API"
) -> None:
    """
    Primary interface for weather data retrieval.
    
    Raises:
        ValueError: Invalid input parameters
        ConnectionError: Network connectivity issues
        DataUnavailableError: Requested data not available
        FormatError: Data format conversion issues
    """
```

#### 5.1.2 Data Validation Interface
```python
class InputValidator:
    """Validates all input parameters."""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """Validate latitude/longitude bounds."""
        return -90 <= lat <= 90 and -180 <= lon <= 180
        
    @staticmethod
    def validate_date_range(start: date, end: date) -> bool:
        """Validate date range logic."""
        return start <= end and start >= date(1981, 1, 1)
        
    @staticmethod
    def validate_source(source: str) -> bool:
        """Validate data source specification."""
        return source.upper() in ["S3", "API"]
```

### 5.2 Internal Interface Contracts

#### 5.2.1 Data Source Interface
```python
from abc import ABC, abstractmethod

class WeatherDataSource(ABC):
    """Abstract interface for weather data sources."""
    
    @abstractmethod
    async def fetch_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        variables: List[str]
    ) -> Dict[str, Any]:
        """Fetch weather data from source."""
        pass
        
    @abstractmethod
    def is_available(self, date_range: Tuple[date, date]) -> bool:
        """Check if source can provide data for date range."""
        pass
```

#### 5.2.2 Format Converter Interface
```python
class FormatConverter(ABC):
    """Abstract interface for data format conversion."""
    
    @abstractmethod
    def convert(
        self,
        source_data: Dict[str, Any],
        target_format: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Convert data between formats."""
        pass
        
    @abstractmethod
    def validate_output(self, converted_data: str) -> bool:
        """Validate converted data format."""
        pass
```

---

## 6. Database Design

### 6.1 Data Storage Strategy

#### 6.1.1 File-Based Storage
```
data/
├── cache/
│   ├── zarr_datasets/         # Cached Zarr dataset metadata
│   ├── elevation_cache.pkl    # Elevation lookup cache
│   └── api_responses/         # Temporary API response cache
├── output/
│   ├── *.wth                 # Generated ICASA weather files
│   └── metadata/             # File generation metadata
└── system/
    ├── logs/                 # System operation logs
    └── config/               # Runtime configuration
```

#### 6.1.2 Metadata Schema
```python
class WeatherFileMetadata:
    """Metadata for generated weather files."""
    
    file_path: str
    generation_timestamp: datetime
    source_type: str          # "API" or "S3"
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    variables_included: List[str]
    data_quality_score: float # 0.0 - 1.0
    file_checksum: str
```

### 6.2 Caching Database Design

```python
class CacheEntry:
    """Cache entry structure."""
    
    cache_key: str            # Unique identifier
    data_type: str           # "file", "dataset", "elevation"
    created_at: datetime
    expires_at: datetime
    access_count: int
    data_size_bytes: int
    file_path: Optional[str]
    
class CacheIndex:
    """In-memory cache index for fast lookups."""
    
    entries: Dict[str, CacheEntry]
    access_order: List[str]  # For LRU eviction
    total_size: int
    max_size: int = 1_000_000_000  # 1GB default
```

---

## 7. Security Design

### 7.1 Data Access Security

#### 7.1.1 External API Security
```python
class APISecurityManager:
    """Manages secure API communications."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=100, window=3600)
        self.request_validator = RequestValidator()
        
    async def secure_request(self, url: str, params: Dict) -> httpx.Response:
        """
        Security measures:
        1. Rate limiting to prevent abuse
        2. Request parameter validation
        3. SSL/TLS verification
        4. Timeout enforcement
        5. Response validation
        """
```

#### 7.1.2 File System Security
```python
class FileSystemSecurity:
    """File system access security."""
    
    @staticmethod
    def validate_path(file_path: Path) -> bool:
        """
        Path validation:
        1. Prevent directory traversal attacks
        2. Ensure paths within designated directories
        3. Validate file extensions
        4. Check write permissions
        """
        
    @staticmethod
    def secure_file_write(content: str, path: Path) -> bool:
        """
        Secure file operations:
        1. Atomic writes (temp file + rename)
        2. Permission validation
        3. Disk space checks
        4. Content validation
        """
```

### 7.2 Input Validation Security

```python
class SecurityValidator:
    """Security-focused input validation."""
    
    @staticmethod
    def sanitize_coordinates(lat: float, lon: float) -> Tuple[float, float]:
        """Sanitize coordinate inputs to prevent injection."""
        
    @staticmethod
    def validate_date_inputs(start: date, end: date) -> bool:
        """Validate date inputs for reasonable ranges."""
        
    @staticmethod
    def sanitize_file_names(name: str) -> str:
        """Sanitize file names to prevent path injection."""
```

---

## 8. Performance Design

### 8.1 Asynchronous Architecture

#### 8.1.1 Concurrency Model
```python
class AsyncExecutionManager:
    """Manages asynchronous execution patterns."""
    
    def __init__(self):
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
    async def execute_with_concurrency_limit(
        self,
        coro: Coroutine
    ) -> Any:
        """Execute coroutine with concurrency limiting."""
        async with self.semaphore:
            return await coro
```

#### 8.1.2 I/O Optimization
```python
class IOOptimizer:
    """Optimizes I/O operations."""
    
    async def batch_zarr_operations(
        self,
        operations: List[Callable]
    ) -> List[Any]:
        """
        Batch Zarr operations for efficiency:
        1. Group operations by dataset
        2. Minimize dataset opens/closes
        3. Use connection pooling
        4. Implement read-ahead caching
        """
```

### 8.2 Memory Management

#### 8.2.1 Memory-Efficient Data Processing
```python
class MemoryManager:
    """Manages memory usage for large datasets."""
    
    def __init__(self):
        self.max_memory_mb = 512
        self.chunk_size = 1000  # Process data in chunks
        
    async def process_large_dataset(
        self,
        dataset: xr.Dataset,
        operation: Callable
    ) -> Any:
        """
        Memory-efficient processing:
        1. Chunk-based processing
        2. Lazy evaluation where possible
        3. Garbage collection hints
        4. Memory usage monitoring
        """
```

### 8.3 Performance Monitoring

```python
class PerformanceMonitor:
    """Monitors system performance metrics."""
    
    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'average_response_time': 0.0,
            'error_rate': 0.0,
            'cache_hit_rate': 0.0,
            'memory_usage': 0.0
        }
        
    @contextmanager
    def measure_execution_time(self, operation_name: str):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.record_metric(operation_name, execution_time)
```

---

## 9. Error Handling Design

### 9.1 Error Classification

#### 9.1.1 Error Hierarchy
```python
class WeatherSystemError(Exception):
    """Base exception for weather system errors."""
    pass

class NetworkError(WeatherSystemError):
    """Network-related errors."""
    pass

class DataUnavailableError(WeatherSystemError):
    """Data not available for requested parameters."""
    pass

class FormatError(WeatherSystemError):
    """Data format conversion errors."""
    pass

class ValidationError(WeatherSystemError):
    """Input validation errors."""
    pass
```

#### 9.1.2 Error Recovery Strategies
```python
class ErrorRecoveryManager:
    """Manages error recovery strategies."""
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Recovery strategies by error type:
        
        NetworkError:
          1. Exponential backoff retry
          2. Switch to alternative source
          3. Use cached data if available
          
        DataUnavailableError:
          1. Try alternative date range
          2. Switch data sources
          3. Partial data retrieval
          
        FormatError:
          1. Data validation and cleaning
          2. Alternative format conversion
          3. Manual intervention flag
        """
```

### 9.2 Logging and Monitoring

#### 9.2.1 Structured Logging
```python
class StructuredLogger:
    """Provides structured logging for system events."""
    
    def __init__(self):
        self.logger = logging.getLogger('pythia_weather')
        self.setup_handlers()
        
    def log_request(
        self,
        request_id: str,
        latitude: float,
        longitude: float,
        date_range: Tuple[date, date],
        source: str
    ):
        """Log request details with structured format."""
        
    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        request_id: str
    ):
        """Log error with full context information."""
```

### 9.3 Health Monitoring

```python
class HealthMonitor:
    """Monitors system health and availability."""
    
    async def check_api_health(self) -> Dict[str, Any]:
        """Check NASA POWER API availability."""
        
    async def check_s3_health(self) -> Dict[str, Any]:
        """Check S3/Zarr data source availability."""
        
    async def system_health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check."""
        return {
            'api_status': await self.check_api_health(),
            's3_status': await self.check_s3_health(),
            'memory_usage': self.get_memory_usage(),
            'disk_space': self.get_disk_space(),
            'cache_status': self.get_cache_status()
        }
```

---

## 10. Deployment Architecture

### 10.1 Environment Configuration

#### 10.1.1 Development Environment
```yaml
# dev_config.yaml
environment: development
logging_level: DEBUG
cache_enabled: true
cache_size_mb: 100
api_timeout: 30
max_retries: 2
data_directory: ./data/dev
```

#### 10.1.2 Production Environment
```yaml
# prod_config.yaml
environment: production
logging_level: INFO
cache_enabled: true
cache_size_mb: 1000
api_timeout: 60
max_retries: 3
data_directory: /var/data/pythia_weather
```

### 10.2 Containerization Strategy

#### 10.2.1 Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libnetcdf-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from weather import health_check; asyncio.run(health_check())"

# Run application
CMD ["python", "-m", "weather"]
```

### 10.3 Scalability Considerations

#### 10.3.1 Horizontal Scaling
```python
class LoadBalancer:
    """Distributes requests across multiple instances."""
    
    def __init__(self):
        self.instances = []
        self.current_index = 0
        
    def get_next_instance(self) -> str:
        """Round-robin load distribution."""
        instance = self.instances[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.instances)
        return instance
```

---

## 11. Testing Strategy

### 11.1 Unit Testing

#### 11.1.1 Component Testing Strategy
```python
class TestWeatherOrchestrator(unittest.TestCase):
    """Unit tests for main orchestrator."""
    
    def setUp(self):
        self.orchestrator = WeatherDataOrchestrator()
        self.mock_api_client = Mock()
        self.mock_s3_client = Mock()
        
    async def test_source_selection_logic(self):
        """Test intelligent source selection."""
        
    async def test_fallback_mechanism(self):
        """Test fallback to alternative source."""
        
    async def test_error_handling(self):
        """Test comprehensive error handling."""
```

#### 11.1.2 Data Source Testing
```python
class TestAPIDataSource(unittest.TestCase):
    """Unit tests for API data source."""
    
    @patch('httpx.AsyncClient.get')
    async def test_api_request_success(self, mock_get):
        """Test successful API requests."""
        
    @patch('httpx.AsyncClient.get')
    async def test_api_request_retry(self, mock_get):
        """Test retry mechanism on failures."""
        
class TestS3DataSource(unittest.TestCase):
    """Unit tests for S3/Zarr data source."""
    
    @patch('s3fs.S3FileSystem')
    async def test_zarr_data_retrieval(self, mock_s3fs):
        """Test Zarr data retrieval and processing."""
```

### 11.2 Integration Testing

#### 11.2.1 End-to-End Testing
```python
class TestSystemIntegration(unittest.TestCase):
    """Integration tests for complete system."""
    
    async def test_complete_workflow_api(self):
        """Test complete workflow using API source."""
        
    async def test_complete_workflow_s3(self):
        """Test complete workflow using S3 source."""
        
    async def test_fallback_workflow(self):
        """Test fallback from API to S3."""
```

### 11.3 Performance Testing

#### 11.3.1 Load Testing
```python
class TestPerformance(unittest.TestCase):
    """Performance and load testing."""
    
    async def test_concurrent_requests(self):
        """Test system under concurrent load."""
        
    async def test_large_dataset_processing(self):
        """Test processing of large datasets."""
        
    async def test_memory_usage(self):
        """Test memory usage patterns."""
```

---

## 12. Monitoring and Logging

### 12.1 Operational Monitoring

#### 12.1.1 Key Performance Indicators (KPIs)
```python
class SystemMetrics:
    """System performance metrics."""
    
    def __init__(self):
        self.metrics = {
            'requests_per_minute': 0,
            'average_response_time_ms': 0,
            'success_rate_percent': 0,
            'cache_hit_rate_percent': 0,
            'api_availability_percent': 0,
            's3_availability_percent': 0,
            'memory_usage_mb': 0,
            'disk_usage_mb': 0
        }
```

#### 12.1.2 Alerting System
```python
class AlertManager:
    """Manages system alerts and notifications."""
    
    def __init__(self):
        self.alert_thresholds = {
            'error_rate': 0.05,        # 5% error rate
            'response_time': 30000,    # 30 seconds
            'memory_usage': 0.80,      # 80% memory usage
            'disk_usage': 0.90         # 90% disk usage
        }
        
    async def check_alert_conditions(self, metrics: Dict[str, float]):
        """Check metrics against alert thresholds."""
```

### 12.2 Audit Logging

#### 12.2.1 Audit Trail
```python
class AuditLogger:
    """Maintains audit trail for system operations."""
    
    def log_data_request(
        self,
        user_id: str,
        request_params: Dict[str, Any],
        timestamp: datetime
    ):
        """Log data access requests."""
        
    def log_file_generation(
        self,
        file_path: str,
        source_data: Dict[str, Any],
        timestamp: datetime
    ):
        """Log file generation events."""
```

---

## Appendices

### Appendix A: Configuration Reference

#### A.1 Environment Variables
```bash
# Required Environment Variables
PYTHIA_DATA_DIR=/path/to/data
PYTHIA_LOG_LEVEL=INFO
PYTHIA_CACHE_SIZE_MB=1000

# Optional Environment Variables
PYTHIA_API_TIMEOUT=60
PYTHIA_MAX_RETRIES=3
PYTHIA_ENABLE_CACHE=true
```

### Appendix B: API Reference

#### B.1 Complete API Documentation
```python
# Full API signature with all parameters
async def download_weather_data(
    latitude: float,                    # Required: -90 to 90
    longitude: float,                   # Required: -180 to 180
    start_date: date,                   # Required: >= 1981-01-01
    end_date: date,                     # Required: <= today
    include_srad: bool = True,          # Optional: Include solar radiation
    include_met: bool = True,           # Optional: Include meteorological data
    source: str = "S3",                 # Optional: "S3" or "API"
    output_dir: Optional[Path] = None,  # Optional: Custom output directory
    station_name: str = "NASA",         # Optional: 4-character station code
    elevation: Optional[float] = None   # Optional: Manual elevation override
) -> Optional[str]:                     # Returns: Path to generated file
    """Complete weather data retrieval interface."""
```

### Appendix C: Error Codes

#### C.1 System Error Codes
```python
ERROR_CODES = {
    'E001': 'Invalid latitude coordinate',
    'E002': 'Invalid longitude coordinate', 
    'E003': 'Invalid date range',
    'E004': 'Network connection failed',
    'E005': 'API rate limit exceeded',
    'E006': 'Data not available for date range',
    'E007': 'S3/Zarr access failed',
    'E008': 'Format conversion failed',
    'E009': 'File write operation failed',
    'E010': 'Elevation data unavailable'
}
```

---

**Document Control**
- Version: 1.0
- Last Updated: October 14, 2025
- Review Date: October 14, 2026
- Approved By: System Architecture Team