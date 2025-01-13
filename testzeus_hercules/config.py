# config_manager.py

import argparse
import json
import os
from typing import Optional

from dotenv import load_dotenv
from testzeus_hercules.utils.logger import logger


class BaseConfigManager:
    """
    The base class that contains the common logic for:
      - argument parsing
      - loading from dict/JSON
      - optional env variable merging
      - directory creation
      - environment checks
    """

    def __init__(self, config_dict: dict, ignore_env: bool = False):
        """
        Initialize the config manager with config_dict as base.

        Args:
            config_dict (dict): The base configuration dictionary.
            ignore_env (bool): If True, environment variables will be ignored.
        """
        self._config = config_dict.copy()
        self._ignore_env = ignore_env

        # 1) Possibly load .env if not in test environment
        is_test_env = os.environ.get("IS_TEST_ENV", "false").lower() == "true"
        if not is_test_env and not self._ignore_env:
            # Load .env if it exists
            env_file_path: str = ".env"
            load_dotenv(env_file_path, verbose=True, override=True)

        # 2) Parse command-line arguments to override env (if not ignoring env)
        if not self._ignore_env:
            self._parse_arguments()

        # 3) Merge environment variables if not ignoring env
        if not self._ignore_env:
            self._merge_from_env()

        # 4) Perform the same LLM checks as your original code
        self._check_llm_config()

        # 5) Provide or finalize certain defaults
        #    (some might have been overridden by env/arguments)
        self._finalize_defaults()

        # A dynamic default test ID in this instance
        self._default_test_id = self._config.get("DEFAULT_TEST_ID", "default")

    # -------------------------------------------------------------------------
    # Class methods to instantiate from dict or JSON
    # -------------------------------------------------------------------------

    @classmethod
    def from_dict(
        cls, config_dict: dict, ignore_env: bool = False
    ) -> "BaseConfigManager":
        return cls(config_dict, ignore_env=ignore_env)

    @classmethod
    def from_json(
        cls, json_file_path: str, ignore_env: bool = False
    ) -> "BaseConfigManager":
        with open(json_file_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return cls(config_dict, ignore_env=ignore_env)

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _parse_arguments(self) -> None:
        """
        Parse Hercules-specific command-line arguments
        and place them into the environment for consistency.
        """
        parser = argparse.ArgumentParser(
            description="Hercules: The World's First Open-Source AI Agent for End-to-End Testing"
        )
        parser.add_argument(
            "--input-file", type=str, help="Path to the input file.", required=False
        )
        parser.add_argument(
            "--output-path",
            type=str,
            help="Path to the output directory.",
            required=False,
        )
        parser.add_argument(
            "--test-data-path",
            type=str,
            help="Path to the test data directory.",
            required=False,
        )
        parser.add_argument(
            "--project-base",
            type=str,
            help="Path to the project base directory.",
            required=False,
        )
        parser.add_argument(
            "--llm-model",
            type=str,
            help="Name of the LLM model.",
            required=False,
        )
        parser.add_argument(
            "--llm-model-api-key",
            type=str,
            help="API key for the LLM model.",
            required=False,
        )

        # Parse known args; ignore unknown if you have other custom arguments
        args, _ = parser.parse_known_args()

        if args.input_file:
            os.environ["INPUT_GHERKIN_FILE_PATH"] = args.input_file
        if args.output_path:
            os.environ["JUNIT_XML_BASE_PATH"] = args.output_path
        if args.test_data_path:
            os.environ["TEST_DATA_PATH"] = args.test_data_path
        if args.project_base:
            os.environ["PROJECT_SOURCE_ROOT"] = args.project_base
        if args.llm_model:
            os.environ["LLM_MODEL_NAME"] = args.llm_model
        if args.llm_model_api_key:
            os.environ["LLM_MODEL_API_KEY"] = args.llm_model_api_key

    def _merge_from_env(self) -> None:
        """
        Merge any relevant environment variables into the configuration dictionary.
        This can be as simple or complex as you want, e.g., partial name matching.
        """
        # A simple approach: if an env var key is in self._config, override it.
        # We'll also add some keys if they're not in self._config at all.
        # Extend based on your needs.

        # The main keys used in your original config:
        relevant_keys = [
            "MODE",
            "PROJECT_SOURCE_ROOT",
            "INPUT_GHERKIN_FILE_PATH",
            "JUNIT_XML_BASE_PATH",
            "TEST_DATA_PATH",
            "BROWSER_TYPE",
            "HEADLESS",
            "RECORD_VIDEO",
            "TAKE_SCREENSHOTS",
            "CAPTURE_NETWORK",
            "CDP_ENDPOINT_URL",
            "LLM_MODEL_NAME",
            "LLM_MODEL_API_KEY",
            "AGENTS_LLM_CONFIG_FILE",
            "AGENTS_LLM_CONFIG_FILE_REF_KEY",
            "HF_HOME",
            "TOKENIZERS_PARALLELISM",
            "DONT_CLOSE_BROWSER",
            "TOKEN_VERBOSE",
            "BROWSER_RESOLUTION",
            "RUN_DEVICE",
            "LOCALE",
            "TIMEZONE",
            "GEOLOCATION",
            "COLOR_SCHEME",
            "LOAD_EXTRA_TOOLS",
            "GEO_PROVIDER",
            "GEO_API_KEY",
        ]

        for key in relevant_keys:
            if key in os.environ:
                self._config[key] = os.environ[key]

        # If there are env vars you'd like to add even if they aren't in _config:
        # for key in relevant_keys:
        #     if key in os.environ and key not in self._config:
        #         self._config[key] = os.environ[key]
        # (Adjust logic to your preference.)

    def _check_llm_config(self) -> None:
        """
        Check that either (LLM_MODEL_NAME & LLM_MODEL_API_KEY) or
        (AGENTS_LLM_CONFIG_FILE & AGENTS_LLM_CONFIG_FILE_REF_KEY) are correctly set.
        """
        llm_model_name = self._config.get("LLM_MODEL_NAME")
        llm_model_api_key = self._config.get("LLM_MODEL_API_KEY")
        agents_llm_config_file = self._config.get("AGENTS_LLM_CONFIG_FILE")
        agents_llm_config_file_ref_key = self._config.get(
            "AGENTS_LLM_CONFIG_FILE_REF_KEY"
        )

        if (llm_model_name and llm_model_api_key) and (
            agents_llm_config_file or agents_llm_config_file_ref_key
        ):
            logger.error(
                "Provide either LLM_MODEL_NAME and LLM_MODEL_API_KEY together, "
                "or AGENTS_LLM_CONFIG_FILE and AGENTS_LLM_CONFIG_FILE_REF_KEY together, not both."
            )
            exit(1)

        if (not llm_model_name or not llm_model_api_key) and (
            not agents_llm_config_file or not agents_llm_config_file_ref_key
        ):
            logger.error(
                "Either LLM_MODEL_NAME and LLM_MODEL_API_KEY must be set together, "
                "or AGENTS_LLM_CONFIG_FILE and AGENTS_LLM_CONFIG_FILE_REF_KEY must be set together. "
                "Use --llm-model and --llm-model-api-key in hercules command."
            )
            exit(1)

    def _finalize_defaults(self) -> None:
        """
        Provide (or override) default values for keys that might not be in self._config.
        Also handles the fallback from your original code.
        """
        self._config.setdefault("MODE", "prod")
        self._config.setdefault("DEFAULT_TEST_ID", "default")

        project_source_root = self._config.get("PROJECT_SOURCE_ROOT", "./opt")
        self._config["PROJECT_SOURCE_ROOT"] = project_source_root

        # Fill in paths if missing
        self._config.setdefault(
            "INPUT_GHERKIN_FILE_PATH",
            os.path.join(project_source_root, "input/test.feature"),
        )
        self._config.setdefault(
            "JUNIT_XML_BASE_PATH", os.path.join(project_source_root, "output")
        )
        self._config.setdefault(
            "TEST_DATA_PATH", os.path.join(project_source_root, "test_data")
        )
        self._config.setdefault(
            "SCREEN_SHOT_PATH", os.path.join(project_source_root, "proofs")
        )
        self._config.setdefault(
            "PROJECT_TEMP_PATH", os.path.join(project_source_root, "temp")
        )
        self._config.setdefault(
            "SOURCE_LOG_FOLDER_PATH", os.path.join(project_source_root, "log_files")
        )
        self._config.setdefault(
            "TMP_GHERKIN_PATH", os.path.join(project_source_root, "gherkin_files")
        )

        # Extra environment defaults from original code
        if "HF_HOME" not in self._config:
            self._config["HF_HOME"] = "./.cache"
        if "TOKENIZERS_PARALLELISM" not in self._config:
            self._config["TOKENIZERS_PARALLELISM"] = "false"

        self._config.setdefault("TOKEN_VERBOSE", "false")
        self._config.setdefault("BROWSER_RESOLUTION", "1920,1080")
        self._config.setdefault("RUN_DEVICE", "desktop")
        self._config.setdefault("LOAD_EXTRA_TOOLS", "false")
        self._config.setdefault("LOCALE", "en-US")
        self._config.setdefault("TIMEZONE", None)
        self._config.setdefault("GEOLOCATION", None)
        self._config.setdefault("COLOR_SCHEME", "light")

        # HEADLESS, RECORD_VIDEO, etc. can also be "finalized" here if needed
        self._config.setdefault("HEADLESS", "true")
        self._config.setdefault("RECORD_VIDEO", "true")
        self._config.setdefault("TAKE_SCREENSHOTS", "true")
        self._config.setdefault("BROWSER_TYPE", "chromium")
        self._config.setdefault("CAPTURE_NETWORK", "true")
        self._config.setdefault("DONT_CLOSE_BROWSER", "false")
        self._config.setdefault("GEO_PROVIDER", None)
        self._config.setdefault("GEO_API_KEY", None)

    # -------------------------------------------------------------------------
    # Public Getters & Setters
    # -------------------------------------------------------------------------

    def get_config(self) -> dict:
        """Return the underlying config dictionary (if you need direct access)."""
        return self._config

    def get_mode(self) -> str:
        return self._config["MODE"]

    def get_project_source_root(self) -> str:
        return self._config["PROJECT_SOURCE_ROOT"]

    def set_default_test_id(self, test_id: str) -> None:
        self._default_test_id = test_id
        self._config["DEFAULT_TEST_ID"] = test_id

    def reset_default_test_id(self) -> None:
        self.set_default_test_id("default")

    def get_default_test_id(self) -> str:
        return self._default_test_id

    def get_dont_close_browser(self) -> bool:
        return self._config["DONT_CLOSE_BROWSER"].lower().strip() == "true"

    def get_cdp_config(self) -> Optional[dict]:
        """
        Return CDP config if `CDP_ENDPOINT_URL` is set.
        """
        cdp_endpoint_url = self._config.get("CDP_ENDPOINT_URL")
        if cdp_endpoint_url:
            return {"endpoint_url": cdp_endpoint_url}
        return None

    def should_run_headless(self) -> bool:
        return self._config["HEADLESS"].lower().strip() == "true"

    def should_record_video(self) -> bool:
        return self._config["RECORD_VIDEO"].lower().strip() == "true"

    def should_take_screenshots(self) -> bool:
        return self._config["TAKE_SCREENSHOTS"].lower().strip() == "true"

    def get_browser_type(self) -> str:
        return self._config["BROWSER_TYPE"]

    def should_capture_network(self) -> bool:
        return self._config["CAPTURE_NETWORK"].lower().strip() == "true"

    def get_hf_home(self) -> str:
        return self._config["HF_HOME"]

    # -------------------------------------------------------------------------
    # Directory creation logic (mirroring your original code)
    # -------------------------------------------------------------------------

    def get_input_gherkin_file_path(self) -> str:
        path = self._config["INPUT_GHERKIN_FILE_PATH"]
        if not os.path.exists(path):
            base_path = os.path.dirname(path)
            if base_path and not os.path.exists(base_path):
                os.makedirs(base_path)
                logger.info(f"Created INPUT_GHERKIN_FILE_PATH folder at: {base_path}")
        return path

    def get_tmp_gherkin_path(self) -> str:
        path = self._config["TMP_GHERKIN_PATH"]
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created TMP_GHERKIN_PATH folder at: {path}")
        return path

    def get_junit_xml_base_path(self) -> str:
        path = self._config["JUNIT_XML_BASE_PATH"]
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created JUNIT_XML_BASE_PATH folder at: {path}")
        return path

    def get_source_log_folder_path(self, test_id: Optional[str] = None) -> str:
        test_id = test_id or self._default_test_id
        path = os.path.join(self._config["SOURCE_LOG_FOLDER_PATH"], test_id)
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created source_log_folder_path folder at: {path}")
        return path

    def get_test_data_path(self) -> str:
        path = self._config["TEST_DATA_PATH"]
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created test data folder at: {path}")
        return path

    def get_proof_path(self, test_id: Optional[str] = None) -> str:
        test_id = test_id or self._default_test_id
        base_path = self._config["SCREEN_SHOT_PATH"]
        path = os.path.join(base_path, test_id)

        if not os.path.exists(path):
            os.makedirs(os.path.join(path, "screenshots"))
            os.makedirs(os.path.join(path, "videos"))
            logger.info(f"Created screen_shot_path folder at: {path}")
        return path

    def get_project_temp_path(self, test_id: Optional[str] = None) -> str:
        test_id = test_id or self._default_test_id
        base_path = self._config["PROJECT_TEMP_PATH"]
        path = os.path.join(base_path, test_id)
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created project_temp_path folder at: {path}")
        return path

    def get_token_verbose(self) -> bool:
        return self._config["TOKEN_VERBOSE"].lower().strip() == "true"

    def get_resolution(self) -> str:
        return self._config["BROWSER_RESOLUTION"]

    def get_run_device(self) -> str:
        return self._config["RUN_DEVICE"]

    def get_load_extra_tools(self) -> str:
        return self._config["LOAD_EXTRA_TOOLS"]

    def get_locale(self) -> str:
        return self._config["LOCALE"]

    def get_timezone(self) -> str:
        return self._config["TIMEZONE"]

    def get_geolocation(self) -> str:
        return self._config["GEOLOCATION"]

    def get_color_scheme(self) -> str:
        return self._config["COLOR_SCHEME"]

    def get_geo_provider(self) -> str:
        return self._config["GEO_PROVIDER"]

    def get_geo_api_key(self) -> str:
        return self._config["GEO_API_KEY"]

    # -------------------------------------------------------------------------
    # Telemetry
    # -------------------------------------------------------------------------

    def send_config_telemetry(self) -> None:
        """
        Send a snapshot of the config to telemetry (like your final block).
        """
        config_brief = {
            "MODE": self.get_mode(),
            "HEADLESS": self.should_run_headless(),
            "RECORD_VIDEO": self.should_record_video(),
            "TAKE_SCREENSHOTS": self.should_take_screenshots(),
            "BROWSER_TYPE": self.get_browser_type(),
            "CAPTURE_NETWORK": self.should_capture_network(),
        }
        add_event(
            EventType.CONFIG,
            EventData(detail="General Config", additional_data=config_brief),
        )


# ------------------------------------------------------------------------------
# Derived classes for Non-Singleton and Singleton usage
# ------------------------------------------------------------------------------


class NonSingletonConfigManager(BaseConfigManager):
    """
    A regular config manager that can be instantiated multiple times
    without any shared state among instances.
    """

    def __init__(self, config_dict: dict, ignore_env: bool = False):
        super().__init__(config_dict=config_dict, ignore_env=ignore_env)


class SingletonConfigManager(BaseConfigManager):
    """
    A singleton config manager that ensures only one instance
    is created. Use `SingletonConfigManager.instance(...)` instead of
    directly calling `__init__`.
    """

    _instance = None

    def __init__(self, config_dict: dict, ignore_env: bool = False):
        super().__init__(config_dict=config_dict, ignore_env=ignore_env)

    @classmethod
    def instance(
        cls, config_dict: Optional[dict] = None, ignore_env: bool = False
    ) -> "SingletonConfigManager":
        """
        Return the shared instance. If an instance does not already exist,
        create one using config_dict (or empty dict if None is supplied).
        Subsequent calls return the same instance.

        If you supply a different `ignore_env` on subsequent calls, note
        it only affects the very first creation (since the instance won't be replaced).
        """
        if cls._instance is None:
            cls._instance = cls(config_dict or {}, ignore_env=ignore_env)
        else:
            # If there's an existing instance and a new config_dict, decide if/how to merge:
            if config_dict is not None:
                cls._instance._config.update(config_dict)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance, allowing a fresh re-initialization.
        """
        cls._instance = None


# ------------------------------------------------------------------------------
# USAGE EXAMPLES (comment these out or remove in production):
# ------------------------------------------------------------------------------

# if __name__ == "__main__":
#     # Example: Non-singleton usage with ignoring env variables
#     # ns_config = NonSingletonConfigManager.from_dict(
#     #     {"MODE": "dev", "PROJECT_SOURCE_ROOT": "/tmp/myproject"}, ignore_env=True
#     # )
#     # logger.info("[NonSingleton] MODE:", ns_config.get_mode())
#     # logger.info("[NonSingleton] Project Source Root:", ns_config.get_project_source_root())

#     # Example: Singleton usage (if you want to unify config across entire app)
CONF = SingletonConfigManager.instance(
    {"MODE": "prod", "PROJECT_SOURCE_ROOT": "./opt"},
    ignore_env=False,
)

# hack to make sure telemetry status loads
from testzeus_hercules.telemetry import EventData, EventType, add_event

logger.info("[Singleton] MODE: %s", CONF.get_mode())
logger.info("[Singleton] Project Source Root: %s", CONF.get_project_source_root())

# Another call to the same Singleton - merges if we pass a new dict
SingletonConfigManager.instance({"DONT_CLOSE_BROWSER": "true"})
logger.info("[Singleton] DONT_CLOSE_BROWSER: %s", CONF.get_dont_close_browser())

# Send final telemetry
CONF.send_config_telemetry()
