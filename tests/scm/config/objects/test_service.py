# tests/scm/config/objects/test_service.py

# Standard library imports
from unittest.mock import MagicMock

# External libraries
import pytest
from requests.exceptions import HTTPError

# Local SDK imports
from scm.config.objects import Service
from scm.exceptions import (
    APIError,
    BadRequestError,
    InvalidObjectError,
    ObjectNotPresentError,
    MalformedCommandError,
    MissingQueryParameterError,
    ReferenceNotZeroError,
)
from scm.models.objects import (
    ServiceResponseModel,
)
from tests.factories import (
    ServiceResponseFactory,
    ServiceCreateApiFactory,
    ServiceUpdateApiFactory,
)
from tests.utils import raise_mock_http_error


@pytest.mark.usefixtures("load_env")
class TestServiceBase:
    """Base class for Service tests."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_scm):
        """Setup method that runs before each test."""
        self.mock_scm = mock_scm  # noqa
        self.mock_scm.get = MagicMock()
        self.mock_scm.post = MagicMock()
        self.mock_scm.put = MagicMock()
        self.mock_scm.delete = MagicMock()
        self.client = Service(self.mock_scm)  # noqa


# -------------------- Test Classes Grouped by Functionality --------------------


class TestServiceList(TestServiceBase):
    """Tests for listing Service objects."""

    def test_list_valid(self):
        """
        **Objective:** Test listing all objects using factories.
        """
        mock_response = {
            "data": [
                ServiceResponseFactory.with_tcp(
                    port="80,8080",
                    name="service-http",
                    folder="All",
                    snippet="predefined-snippet",
                ).model_dump(),
                ServiceResponseFactory.with_tcp(
                    port="443",
                    name="service-https",
                    folder="All",
                    snippet="predefined-snippet",
                ).model_dump(),
                ServiceResponseFactory.with_tcp_override(
                    id="5e7600f1-8681-4048-973b-4117da7e446c",
                    port="4433,4333,4999,9443",
                    timeout=10,
                    halfclose_timeout=10,
                    timewait_timeout=10,
                    name="Test",
                    folder="Shared",
                    description="This is just a test",
                ).model_dump(),
            ]
        }

        self.mock_scm.get.return_value = mock_response  # noqa
        existing_objects = self.client.list(folder="Prisma Access")

        self.mock_scm.get.assert_called_once_with(  # noqa
            "/config/objects/v1/services",
            params={
                "limit": 10000,
                "folder": "Prisma Access",
            },
        )
        assert isinstance(existing_objects, list)
        assert isinstance(existing_objects[0], ServiceResponseModel)
        assert len(existing_objects) == 3
        assert existing_objects[0].name == "service-http"

    def test_list_folder_empty_error(self):
        """Test that empty folder raises appropriate error."""
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="E003",
            message='"folder" is not allowed to be empty',
            error_type="Missing Query Parameter",
        )

        with pytest.raises(MissingQueryParameterError) as exc_info:
            self.client.list(folder="")

        error_msg = str(exc_info.value)
        assert (
            "['\"folder\" is not allowed to be empty'] - HTTP error: 400 - API error: E003"
            in error_msg
        )

    def test_list_folder_nonexistent_error(self):
        """Test error handling in list operation."""
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=404,
            error_code="API_I00013",
            message="Listing failed",
            error_type="Operation Impossible",
        )

        with pytest.raises(ObjectNotPresentError) as exc_info:
            self.client.list(folder="NonexistentFolder")

        error_msg = str(exc_info.value)
        assert (
            "{'errorType': 'Operation Impossible'} - HTTP error: 404 - API error: API_I00013"
            in error_msg
        )

    def test_list_container_missing_error(self):
        """
        Test that InvalidObjectError is raised when no container parameter is provided.
        """
        # Use the utility function to create the mock HTTP error
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="E003",
            message="Exactly one of 'folder', 'snippet', or 'device' must be provided.",
            error_type="Invalid Object",
        )

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.list()
        error_msg = str(exc_info.value)
        assert "HTTP error: 400 - API error: E003" in error_msg

    def test_list_container_multiple_error(self):
        """Test validation of container parameters."""
        # Use the utility function to create the mock HTTP error
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="E003",
            message="Multiple container types provided",
            error_type="Invalid Object",
        )

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.list(folder="folder1", snippet="snippet1")

        error_msg = str(exc_info.value)
        assert "HTTP error: 400 - API error: E003" in error_msg

    def test_list_filters_valid(self):
        """Test that filters are properly added to parameters."""
        filters = {
            "protocols": ["tcp", "udp"],
            "tags": ["tag1", "tag2"],
        }

        mock_response = {"data": []}
        self.mock_scm.get.return_value = mock_response  # noqa

        self.client.list(folder="Shared", **filters)

        self.mock_scm.get.assert_called_once_with(  # noqa
            "/config/objects/v1/services",
            params={
                "limit": 10000,
                "folder": "Shared",
            },
        )

    def test_list_filters_lists_empty(self):
        """Test behavior with empty filter lists."""
        mock_response = {
            "data": [
                {
                    "name": "service-http",
                    "folder": "All",
                    "snippet": "predefined-snippet",
                    "protocol": {"tcp": {"port": "80,8080"}},
                },
                {
                    "name": "service-https",
                    "folder": "All",
                    "snippet": "predefined-snippet",
                    "protocol": {"tcp": {"port": "443"}},
                },
                {
                    "id": "5e7600f1-8681-4048-973b-4117da7e446c",
                    "name": "Test",
                    "folder": "Shared",
                    "protocol": {
                        "tcp": {
                            "port": "4433,4333,4999,9443",
                            "override": {
                                "timeout": 10,
                                "halfclose_timeout": 10,
                                "timewait_timeout": 10,
                            },
                        }
                    },
                    "description": "Test123455",
                },
                {
                    "id": "5a3d6182-c5f1-4b1e-8ec9-e984ae5247fb",
                    "name": "Test123UDP",
                    "folder": "Shared",
                    "description": "UDP test",
                    "protocol": {"udp": {"port": "5444,5432"}},
                    "tag": ["Automation"],
                },
            ],
            "offset": 0,
            "total": 4,
            "limit": 200,
        }
        self.mock_scm.get.return_value = mock_response  # noqa

        # Empty lists should result in no matches
        filtered_objects = self.client.list(
            folder="Shared",
            protocols=[],
        )
        assert len(filtered_objects) == 0

        filtered_objects = self.client.list(
            folder="Shared",
            tags=[],
        )
        assert len(filtered_objects) == 0

    def test_list_filters_types(self):
        """Test validation of filter types in list method."""
        # Mock response for successful case
        mock_response = {
            "data": [
                {
                    "name": "service-http",
                    "folder": "All",
                    "snippet": "predefined-snippet",
                    "protocol": {"tcp": {"port": "80,8080"}},
                },
                {
                    "name": "service-https",
                    "folder": "All",
                    "snippet": "predefined-snippet",
                    "protocol": {"tcp": {"port": "443"}},
                },
                {
                    "id": "5e7600f1-8681-4048-973b-4117da7e446c",
                    "name": "Test",
                    "folder": "Shared",
                    "protocol": {
                        "tcp": {
                            "port": "4433,4333,4999,9443",
                            "override": {
                                "timeout": 10,
                                "halfclose_timeout": 10,
                                "timewait_timeout": 10,
                            },
                        }
                    },
                    "description": "Test123455",
                },
                {
                    "id": "5a3d6182-c5f1-4b1e-8ec9-e984ae5247fb",
                    "name": "Test123UDP",
                    "folder": "Shared",
                    "description": "UDP test",
                    "protocol": {"udp": {"port": "5444,5432"}},
                    "tag": ["Automation"],
                },
            ],
            "offset": 0,
            "total": 4,
            "limit": 200,
        }

        # Test invalid types filter (string instead of list)
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="E003",
            message="'protocols' filter must be a list",
            error_type="Invalid Query Parameter",
        )
        with pytest.raises(BadRequestError) as exc_info:
            self.client.list(folder="Shared", protocols="tcp")
        assert (
            "{'errorType': 'Invalid Query Parameter'} - HTTP error: 400 - API error: E003"
            in str(exc_info.value)
        )

        # Reset side effect for next test
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="E003",
            message="'tags' filter must be a list",
            error_type="Invalid Query Parameter",
        )
        with pytest.raises(BadRequestError) as exc_info:
            self.client.list(folder="Shared", tags="automation")
        assert (
            "{'errorType': 'Invalid Query Parameter'} - HTTP error: 400 - API error: E003"
            in str(exc_info.value)
        )

        # Reset side effect for successful case
        self.mock_scm.get.side_effect = None  # noqa
        self.mock_scm.get.return_value = mock_response  # noqa

        # Test that valid list filters pass validation
        try:
            self.client.list(
                folder="Shared",
                tags=["automation"],
                protocols=["tcp"],
            )
        except BadRequestError:
            pytest.fail("Unexpected BadRequestError raised with valid list filters")

    def test_list_filters_types_validation(self):
        """Test validation of 'protocols' filter specifically."""
        mock_services = []

        # Test with string instead of list
        invalid_filters = {"protocols": "type1"}
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client._apply_filters(mock_services, invalid_filters)

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert error.error_code == "E003"
        assert "{'errorType': 'Invalid Object'}" in str(error)

        # Test with dict instead of list
        invalid_filters = {"protocols": {"types": "type1"}}
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client._apply_filters(mock_services, invalid_filters)

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert "{'errorType': 'Invalid Object'}" in str(error)

    def test_list_filters_tags_validation(self):
        """Test validation of 'tags' filter specifically."""
        mock_services = []

        # Test with string instead of list
        invalid_filters = {"tags": "tag1"}
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client._apply_filters(mock_services, invalid_filters)

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert error.error_code == "E003"
        assert "{'errorType': 'Invalid Object'}" in str(error)

        # Test with dict instead of list
        invalid_filters = {"tags": {"tag": "tag1"}}
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client._apply_filters(mock_services, invalid_filters)

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert "{'errorType': 'Invalid Object'}" in str(error)

    def test_list_filters_protocols_validation(self):
        """Test validation of 'protocols' filter specifically."""
        mock_services = []

        # Test with string instead of list
        invalid_filters = {"protocols": "test123"}
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client._apply_filters(mock_services, invalid_filters)

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert error.error_code == "E003"
        assert error.http_status_code == 500
        assert "{'errorType': 'Invalid Object'}" in str(error)

        # Test with dict instead of list
        invalid_filters = {"protocols": {"tcp": "123"}}
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client._apply_filters(mock_services, invalid_filters)

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert error.error_code == "E003"
        assert error.http_status_code == 500
        assert "{'errorType': 'Invalid Object'}" in str(error)

    def test_list_filters_combinations(self):
        """Test different combinations of valid filters."""
        mock_response = {
            "data": [
                {
                    "name": "service-http",
                    "folder": "All",
                    "snippet": "predefined-snippet",
                    "protocol": {"tcp": {"port": "80,8080"}},
                    "tag": ["Automation"],
                },
                {
                    "name": "service-https",
                    "folder": "All",
                    "snippet": "predefined-snippet",
                    "protocol": {"tcp": {"port": "443"}},
                },
                {
                    "id": "5e7600f1-8681-4048-973b-4117da7e446c",
                    "name": "Test",
                    "folder": "Shared",
                    "protocol": {
                        "tcp": {
                            "port": "4433,4333,4999,9443",
                            "override": {
                                "timeout": 10,
                                "halfclose_timeout": 10,
                                "timewait_timeout": 10,
                            },
                        }
                    },
                    "description": "Test123455",
                },
                {
                    "id": "5a3d6182-c5f1-4b1e-8ec9-e984ae5247fb",
                    "name": "Test123UDP",
                    "folder": "Shared",
                    "description": "UDP test",
                    "protocol": {"udp": {"port": "5444,5432"}},
                    "tag": ["Automation"],
                },
            ],
            "offset": 0,
            "total": 4,
            "limit": 200,
        }
        self.mock_scm.get.return_value = mock_response  # noqa

        # Test combining protocols and tags filters
        filtered_objects = self.client.list(
            folder="All",
            protocols=["tcp"],
            tags=["Automation"],
        )
        assert len(filtered_objects) == 1
        assert filtered_objects[0].name == "service-http"

    def test_list_response_invalid_format(self):
        """
        Test that InvalidObjectError is raised when the response is not a dictionary.
        """
        # Mock the API client to return a non-dictionary response
        self.mock_scm.get.return_value = ["not", "a", "dictionary"]  # noqa

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.list(folder="Shared")

        assert exc_info.value.error_code == "E003"
        assert exc_info.value.http_status_code == 500
        assert "HTTP error: 500 - API error: E003" in str(exc_info.value)

    def test_list_response_invalid_data_field_missing(self):
        """
        Test that InvalidObjectError is raised when API returns response with missing data field.

        This tests the case where the API response is a dictionary but missing the required 'data' field,
        expecting an InvalidObjectError with specific error details.
        """
        # Mock the API to return a dictionary without 'data' field
        self.mock_scm.get.return_value = {"wrong_field": "value"}  # noqa

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.list(folder="Shared")

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert error.error_code == "E003"
        assert error.http_status_code == 500
        assert "HTTP error: 500 - API error: E003" in str(error)

    def test_list_response_invalid_data_field_type(self):
        """
        Test that InvalidObjectError is raised when API returns non-list data field.

        This tests the case where the API response's 'data' field is not a list,
        expecting an InvalidObjectError with specific error details.
        """
        # Mock the API to return a response where 'data' is not a list
        self.mock_scm.get.return_value = {"data": "not a list"}  # noqa

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.list(folder="Shared")

        error = exc_info.value
        assert isinstance(error, InvalidObjectError)
        assert error.error_code == "E003"
        assert error.http_status_code == 500

    def test_list_response_no_content(self):
        """Test that an HTTPError without response content in list() re-raises the exception."""
        mock_response = MagicMock()
        mock_response.content = None  # Simulate no content
        mock_response.status_code = 500

        mock_http_error = HTTPError(response=mock_response)
        self.mock_scm.get.side_effect = mock_http_error  # noqa

        with pytest.raises(HTTPError):
            self.client.list(folder="Shared")

    def test_list_server_error(self):
        """Test generic exception handling in list method."""
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=500,
            error_code="E003",
            message="An internal error occurred",
            error_type="Internal Error",
        )

        with pytest.raises(APIError) as exc_info:
            self.client.list(folder="Shared")

        error_msg = str(exc_info.value)
        assert (
            "{'errorType': 'Internal Error'} - HTTP error: 500 - API error: E003"
            in error_msg
        )


class TestServiceCreate(TestServiceBase):
    """Tests for creating Service objects."""

    def test_create_valid_tcp(self):
        """Test creating an object with ip_netmask."""
        test_object = ServiceCreateApiFactory.with_tcp()
        mock_response = ServiceResponseFactory.from_request(test_object)

        self.mock_scm.post.return_value = mock_response.model_dump()  # noqa
        created_object = self.client.create(test_object.model_dump(exclude_unset=True))

        self.mock_scm.post.assert_called_once_with(  # noqa
            "/config/objects/v1/services",
            json=test_object.model_dump(exclude_unset=True),
        )
        assert created_object.name == test_object.name
        assert created_object.description == test_object.description
        assert created_object.protocol == test_object.protocol
        assert created_object.folder == test_object.folder

    def test_create_valid_udp(self):
        """Test creating an object with ip_netmask."""
        test_object = ServiceCreateApiFactory.with_udp()
        mock_response = ServiceResponseFactory.from_request(test_object)

        self.mock_scm.post.return_value = mock_response.model_dump()  # noqa
        created_object = self.client.create(test_object.model_dump(exclude_unset=True))

        self.mock_scm.post.assert_called_once_with(  # noqa
            "/config/objects/v1/services",
            json=test_object.model_dump(exclude_unset=True),
        )
        assert created_object.name == test_object.name
        assert created_object.description == test_object.description
        assert created_object.protocol == test_object.protocol
        assert created_object.folder == test_object.folder

    def test_create_http_error_no_response_content(self):
        """Test create method when HTTP error has no response content."""
        # Create a mock response object without content
        mock_response = MagicMock()
        mock_response.content = None
        mock_response.status_code = 500

        # Create an HTTPError with the mock response
        mock_http_error = HTTPError(response=mock_response)

        # Set the side effect of the post method to raise the HTTPError
        self.mock_scm.post.side_effect = mock_http_error  # noqa

        with pytest.raises(HTTPError):
            self.client.create(
                {
                    "name": "test",
                    "protocol": {"tcp": {"port": "80,8080"}},
                    "folder": "test",
                }
            )

    def test_create_object_error_handling(self):
        """
        **Objective:** Test error handling during object creation.
        """
        test_data = ServiceCreateApiFactory.with_tcp()

        # Configure mock to raise HTTPError with the mock response
        self.mock_scm.post.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="API_I00013",
            message="Object creation failed",
            error_type="Object Already Exists",
        )

        with pytest.raises(APIError) as exc_info:
            self.client.create(test_data.model_dump())

        error = exc_info.value
        assert error.error_code == "API_I00013"
        assert (
            "{'errorType': 'Object Already Exists'} - HTTP error: 400 - API error: API_I00013"
            in str(error)
        )

    def test_create_generic_exception_handling(self):
        """Test handling of a generic exception during create."""
        self.mock_scm.post.side_effect = Exception("Generic error")  # noqa

        with pytest.raises(Exception) as exc_info:
            self.client.create(
                {
                    "folder": "tests",
                    "name": "tests",
                    "protocol": {"tcp": {"port": "80,8080"}},
                }
            )
        assert str(exc_info.value) == "Generic error"


class TestServiceGet(TestServiceBase):
    """Tests for retrieving a specific Service object."""

    def test_get_valid_object(self):
        """
        **Objective:** Test retrieving a specific object using factories.
        """
        mock_response = ServiceResponseFactory.with_tcp(
            id="5e7600f1-8681-4048-973b-4117da7e446c",
            name="Test",
            folder="Shared",
            description="This is just a test",
            port="80,8080",
            tag=["Automation"],
        )

        self.mock_scm.get.return_value = mock_response.model_dump()  # noqa
        object_id = mock_response.id

        retrieved_object = self.client.get(object_id)

        self.mock_scm.get.assert_called_once_with(  # noqa
            f"/config/objects/v1/services/{object_id}"
        )
        assert isinstance(retrieved_object, ServiceResponseModel)
        assert retrieved_object.id == mock_response.id
        assert retrieved_object.name == "Test"
        assert retrieved_object.protocol.tcp.port == "80,8080"
        assert retrieved_object.folder == mock_response.folder

    def test_get_object_not_present_error(self):
        """Test error handling when the object is not present."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=404,
            error_code="API_I00013",
            message="Object not found",
            error_type="Object Not Present",
        )

        with pytest.raises(ObjectNotPresentError) as exc_info:
            self.client.get(object_id)

        assert (
            "{'errorType': 'Object Not Present'} - HTTP error: 404 - API error: API_I00013"
            in str(exc_info.value)
        )

    def test_get_generic_exception_handling(self):
        """Test generic exception handling in get method."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        self.mock_scm.get.side_effect = Exception("Generic error")  # noqa

        with pytest.raises(Exception) as exc_info:
            self.client.get(object_id)

        assert str(exc_info.value) == "Generic error"

    def test_get_http_error_no_response_content(self):
        """Test get method when HTTP error has no response content."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        mock_response = MagicMock()
        mock_response.content = None  # Simulate no content
        mock_response.status_code = 500

        mock_http_error = HTTPError(response=mock_response)
        self.mock_scm.get.side_effect = mock_http_error  # noqa

        with pytest.raises(HTTPError):
            self.client.get(object_id)

    def test_get_server_error(self):
        """Test handling of server errors during get method."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=500,
            error_code="E003",
            message="An internal error occurred",
            error_type="Internal Error",
        )

        with pytest.raises(APIError) as exc_info:
            self.client.get(object_id)

        error_msg = str(exc_info.value)
        assert (
            "{'errorType': 'Internal Error'} - HTTP error: 500 - API error: E003"
            in error_msg
        )


class TestServiceUpdate(TestServiceBase):
    """Tests for updating Service objects."""

    def test_update_valid_object(self):
        """
        **Objective:** Test updating an object using factories.
        """

        # Create update data using factory
        update_data = ServiceUpdateApiFactory.with_tcp(
            name="UpdatedService",
            folder="Shared",
            description="An updated service",
            port="80,8080",
        )
        input_data = update_data.model_dump()

        # Create mock response
        mock_response = ServiceResponseFactory.from_request(update_data)
        self.mock_scm.put.return_value = mock_response.model_dump()  # noqa

        # Perform update
        updated_object = self.client.update(input_data)

        # Assert the put method was called with correct parameters
        self.mock_scm.put.assert_called_once_with(  # noqa
            f"/config/objects/v1/services/{update_data.id}",
            json=input_data,
        )

        # Assert the updated object matches the mock response
        assert isinstance(updated_object, ServiceResponseModel)
        assert updated_object.protocol.tcp.port == "80,8080"
        assert updated_object.name == mock_response.name
        assert updated_object.description == mock_response.description
        assert updated_object.folder == mock_response.folder

    def test_update_malformed_command_error(self):
        """Test error handling when update fails due to malformed command."""
        # Create update data using factory
        update_data = ServiceUpdateApiFactory.with_tcp(
            id="123e4567-e89b-12d3-a456-426655440000",
            name="UpdatedService",
            folder="Shared",
            description="An updated service",
            port="80,8080",
        )
        input_data = update_data.model_dump()

        # Use utility function to create mock HTTP error
        self.mock_scm.put.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="API_I00013",
            message="Update failed",
            error_type="Malformed Command",
        )

        with pytest.raises(MalformedCommandError) as exc_info:
            self.client.update(input_data)

        assert (
            "{'errorType': 'Malformed Command'} - HTTP error: 400 - API error: API_I00013"
            in str(exc_info.value)
        )

    def test_update_object_not_present_error(self):
        """Test error handling when the object to update is not present."""
        # Create test data
        update_data = ServiceResponseFactory.with_tcp(
            name="UpdatedService",
            folder="Shared",
            description="An updated service",
            port="80,8080",
        )
        input_data = update_data.model_dump()

        # Use utility function to simulate object not present error
        self.mock_scm.put.side_effect = raise_mock_http_error(  # noqa
            status_code=404,
            error_code="API_I00013",
            message="Object not found",
            error_type="Object Not Present",
        )

        with pytest.raises(ObjectNotPresentError) as exc_info:
            self.client.update(input_data)

        assert (
            "{'errorType': 'Object Not Present'} - HTTP error: 404 - API error: API_I00013"
            in str(exc_info.value)
        )

    def test_update_http_error_no_response_content(self):
        """Test update method when HTTP error has no response content."""
        # Create a mock response object without content
        mock_response = MagicMock()
        mock_response.content = None
        mock_response.status_code = 500

        # Create an HTTPError with the mock response
        mock_http_error = HTTPError(response=mock_response)
        self.mock_scm.put.side_effect = mock_http_error  # noqa

        with pytest.raises(HTTPError):
            self.client.update(
                {
                    "id": "123e4567-e89b-12d3-a456-426655440000",
                    "name": "test",
                    "protocol": {"tcp": {"port": "80,8080"}},
                }
            )

    def test_update_generic_exception_handling(self):
        """Test handling of a generic exception during update."""
        self.mock_scm.put.side_effect = Exception("Generic error")  # noqa

        with pytest.raises(Exception) as exc_info:
            self.client.update(
                {
                    "id": "123e4567-e89b-12d3-a456-426655440000",
                    "name": "test",
                    "protocol": {"tcp": {"port": "80,8080"}},
                }
            )
        assert str(exc_info.value) == "Generic error"

    def test_update_server_error(self):
        """Test handling of server errors during update."""
        # Create test data
        update_data = ServiceUpdateApiFactory.with_tcp(
            id="123e4567-e89b-12d3-a456-426655440000",
            name="UpdatedService",
            folder="Shared",
            description="An updated service",
            port="80,8080",
        )
        input_data = update_data.model_dump()

        # Use utility function to simulate server error
        self.mock_scm.put.side_effect = raise_mock_http_error(  # noqa
            status_code=500,
            error_code="E003",
            message="An internal error occurred",
            error_type="Internal Error",
        )

        with pytest.raises(APIError) as exc_info:
            self.client.update(input_data)

        assert (
            "{'errorType': 'Internal Error'} - HTTP error: 500 - API error: E003"
            in str(exc_info.value)
        )


class TestServiceDelete(TestServiceBase):
    """Tests for deleting Service objects."""

    def test_delete_success(self):
        """Test successful deletion of an object."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        self.mock_scm.delete.return_value = None  # noqa

        # Should not raise any exception
        self.client.delete(object_id)

        # Verify the delete call
        self.mock_scm.delete.assert_called_once_with(  # noqa
            f"/config/objects/v1/services/{object_id}"
        )

    def test_delete_referenced_object(self):
        """
        **Objective:** Test deleting an application that is referenced by another group.
        """
        object_id = "3fecfe58-af0c-472b-85cf-437bb6df2929"

        # Configure mock to raise HTTPError with our custom error response
        self.mock_scm.delete.side_effect = raise_mock_http_error(  # noqa
            status_code=409,
            error_code="E009",
            message="Your configuration is not valid.",
            error_type="Reference Not Zero",
        )

        with pytest.raises(ReferenceNotZeroError) as exc_info:
            self.client.delete(object_id)

        error_message = str(exc_info.value)
        assert "{'errorType': 'Reference Not Zero'}" in error_message
        assert "HTTP error: 409" in error_message
        assert "API error: E009" in error_message

    def test_delete_object_not_present_error(self):
        """Test error handling when the object to delete is not present."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        self.mock_scm.delete.side_effect = raise_mock_http_error(  # noqa
            status_code=404,
            error_code="API_I00013",
            message="Object not found",
            error_type="Object Not Present",
        )

        with pytest.raises(ObjectNotPresentError) as exc_info:
            self.client.delete(object_id)

        error_message = str(exc_info.value)
        assert "{'errorType': 'Object Not Present'}" in error_message
        assert "HTTP error: 404" in error_message
        assert "API error: API_I00013" in error_message

    def test_delete_http_error_no_response_content(self):
        """Test delete method when HTTP error has no response content."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        mock_response = MagicMock()
        mock_response.content = None
        mock_response.status_code = 500

        mock_http_error = HTTPError(response=mock_response)
        self.mock_scm.delete.side_effect = mock_http_error  # noqa

        with pytest.raises(HTTPError):
            self.client.delete(object_id)

    def test_delete_generic_exception_handling(self):
        """Test handling of a generic exception during delete."""
        self.mock_scm.delete.side_effect = Exception("Generic error")  # noqa

        with pytest.raises(Exception) as exc_info:
            self.client.delete("abcdefg")

        assert str(exc_info.value) == "Generic error"

    def test_delete_server_error(self):
        """Test handling of server errors during delete."""
        object_id = "123e4567-e89b-12d3-a456-426655440000"

        self.mock_scm.delete.side_effect = raise_mock_http_error(  # noqa
            status_code=500,
            error_code="E003",
            message="An internal error occurred",
            error_type="Internal Error",
        )

        with pytest.raises(APIError) as exc_info:
            self.client.delete(object_id)

        error_message = str(exc_info.value)
        assert "{'errorType': 'Internal Error'}" in error_message
        assert "HTTP error: 500" in error_message
        assert "API error: E003" in error_message


class TestServiceFetch(TestServiceBase):
    """Tests for fetching Service objects by name."""

    def test_fetch_valid_object(self):
        """Test retrieving an object by its name using the `fetch` method."""
        mock_response_model = ServiceResponseFactory.with_tcp(
            id="123e4567-e89b-12d3-a456-426655440000",
            name="web-browsing",
            folder="Shared",
            port="80,8080",
            description=None,
            tag=["web"],
        )
        mock_response_data = mock_response_model.model_dump()

        # Set the mock to return the response data directly
        self.mock_scm.get.return_value = mock_response_data  # noqa

        # Call the fetch method
        fetched_object = self.client.fetch(
            name=mock_response_model.name,
            folder=mock_response_model.folder,
        )

        # Assert that the GET request was made with the correct parameters
        self.mock_scm.get.assert_called_once_with(  # noqa
            "/config/objects/v1/services",
            params={
                "folder": mock_response_model.folder,
                "name": mock_response_model.name,
            },
        )

        # Validate the returned object
        assert isinstance(fetched_object, dict)
        assert fetched_object["id"] == mock_response_model.id
        assert fetched_object["name"] == mock_response_model.name
        assert fetched_object["tag"] == mock_response_model.tag

    def test_fetch_object_not_present_error(self):
        """
        **Objective:** Test that fetching a non-existent object raises NotFoundError.
        """
        service_name = "NonExistent"
        folder_name = "Shared"

        # Configure mock to raise HTTPError with the mock response
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=404,
            error_code="API_I00013",
            message="Your configuration is not valid. Please review the error message for more details.",
            error_type="Object Not Present",
        )

        with pytest.raises(ObjectNotPresentError):
            self.client.fetch(name=service_name, folder=folder_name)

    def test_fetch_empty_name_error(self):
        """Test fetching with an empty name parameter."""
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="E003",
            message='"name" is not allowed to be empty',
            error_type="Missing Query Parameter",
        )

        with pytest.raises(MissingQueryParameterError) as exc_info:
            self.client.fetch(name="", folder="Shared")

        error_msg = str(exc_info.value)
        assert '"name" is not allowed to be empty' in error_msg
        assert "HTTP error: 400" in error_msg
        assert "API error: E003" in error_msg

    def test_fetch_empty_container_error(self):
        """Test fetching with an empty folder parameter."""
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=400,
            error_code="E003",
            message='"folder" is not allowed to be empty',
            error_type="Missing Query Parameter",
        )

        with pytest.raises(MissingQueryParameterError) as exc_info:
            self.client.fetch(name="test", folder="")

        error_msg = str(exc_info.value)
        assert '"folder" is not allowed to be empty' in error_msg
        assert "HTTP error: 400" in error_msg
        assert "API error: E003" in error_msg

    def test_fetch_invalid_response_format_error(self):
        """Test fetching an object when the API returns an unexpected format."""
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=500,
            error_code="E003",
            message="Invalid response format",
            error_type="Invalid Object",
        )

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.fetch(name="test", folder="Shared")

        error_msg = str(exc_info.value)
        assert "{'errorType': 'Invalid Object'}" in error_msg
        assert "HTTP error: 500" in error_msg
        assert "API error: E003" in error_msg

    # def test_fetch_generic_exception_handling(self):
    #     """Test generic exception handling during fetch."""
    #     self.mock_scm.get.side_effect = Exception("Generic error")  # noqa
    #
    #     with pytest.raises(Exception) as exc_info:
    #         self.client.fetch(name="test", folder="Shared")
    #
    #     assert str(exc_info.value) == "Generic error"

    def test_fetch_http_error_no_response_content(self):
        """Test that an HTTPError without response content in fetch() re-raises the exception."""
        # Create a mock response object without content
        mock_response = MagicMock()
        mock_response.content = None
        mock_response.status_code = 500

        # Create an HTTPError with the mock response
        mock_http_error = HTTPError(response=mock_response)

        # Set the side effect of the get method to raise the HTTPError
        self.mock_scm.get.side_effect = mock_http_error  # noqa

        with pytest.raises(HTTPError):
            self.client.fetch(name="test-address", folder="Shared")

    def test_fetch_server_error(self):
        """Test handling of server errors during fetch."""
        self.mock_scm.get.side_effect = raise_mock_http_error(  # noqa
            status_code=500,
            error_code="E003",
            message="An internal error occurred",
            error_type="Internal Error",
        )

        with pytest.raises(APIError) as exc_info:
            self.client.fetch(name="test", folder="Shared")

        error_msg = str(exc_info.value)
        assert "{'errorType': 'Internal Error'}" in error_msg
        assert "HTTP error: 500" in error_msg
        assert "API error: E003" in error_msg

    def test_fetch_response_handling(self):
        """
        **Objective:** Test fetch method's response handling using factories.
        """
        mock_response = ServiceResponseFactory.with_tcp_override(
            id="123e4567-e89b-12d3-a456-426655440000",
            name="TestService",
            folder="Shared",
            port="80",
            description=None,
            tag=None,
            snippet=None,
        ).model_dump(exclude_unset=True)

        self.mock_scm.get.return_value = mock_response  # noqa

        result = self.client.fetch(name="TestService", folder="Shared")

        # Verify None values are excluded
        assert "description" not in result
        assert "tag" not in result
        assert "snippet" not in result
        assert "override" not in result["protocol"]["tcp"]

        # Verify required fields are present
        assert "id" in result
        assert "name" in result
        assert "protocol" in result
        assert result["protocol"]["tcp"]["port"] == "80"

    def test_fetch_missing_id_field_error(self):
        """Test that InvalidObjectError is raised when the response is missing 'id' field."""
        # Mock response without 'id' field
        mock_response = {
            "name": "test-address",
            "folder": "Shared",
            "ip_netmask": "10.0.0.0/24",
        }

        self.mock_scm.get.return_value = mock_response  # noqa

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.fetch(name="test-address", folder="Shared")

        error_msg = str(exc_info.value)
        assert "HTTP error: 500 - API error: E003" in error_msg
        assert exc_info.value.error_code == "E003"
        assert exc_info.value.http_status_code == 500

    def test_fetch_no_container_provided_error(self):
        """Test that InvalidObjectError is raised when no container parameter is provided."""
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.fetch(name="test-address")

        error_msg = str(exc_info.value)
        assert "HTTP error: 400 - API error: E003" in error_msg
        assert exc_info.value.error_code == "E003"
        assert exc_info.value.http_status_code == 400

    def test_fetch_multiple_containers_provided_error(self):
        """Test that InvalidObjectError is raised when multiple container parameters are provided."""
        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.fetch(
                name="test-address",
                folder="Shared",
                snippet="TestSnippet",
            )

        error_msg = str(exc_info.value)
        assert "HTTP error: 400 - API error: E003" in error_msg
        assert exc_info.value.error_code == "E003"
        assert exc_info.value.http_status_code == 400

    def test_fetch_invalid_response_type_error(self):
        """Test that InvalidObjectError is raised when the response is not a dictionary."""
        # Mock the API client to return a non-dictionary response
        self.mock_scm.get.return_value = ["not", "a", "dictionary"]  # noqa

        with pytest.raises(InvalidObjectError) as exc_info:
            self.client.fetch(name="test123", folder="Shared")

        error_msg = str(exc_info.value)
        assert "HTTP error: 500 - API error: E003" in error_msg
        assert exc_info.value.error_code == "E003"
        assert exc_info.value.http_status_code == 500


# -------------------- End of Test Classes --------------------