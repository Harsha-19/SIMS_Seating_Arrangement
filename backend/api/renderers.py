from rest_framework.renderers import JSONRenderer

class StandardizedJSONRenderer(JSONRenderer):
    """
    Custom renderer to standardize all API responses to:
    {
        "success": true/false,
        "data": ... or null,
        "message": ... (optional)
    }
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')
        success = 200 <= response.status_code < 300
        
        # Bypass wrapping if the response is already in our desired standardized format
        # or if it's a success response that already has the expected top-level keys
        if isinstance(data, dict):
            is_standardized = 'success' in data or 'data' in data
            has_top_level_keys = success and any(k in data for k in ('results', 'counts', 'stats'))
            
            if is_standardized or has_top_level_keys:
                if success and 'success' not in data:
                    data['success'] = True
                return super().render(data, accepted_media_type, renderer_context)

        # Standard wrapping logic
        standardized_data = {
            'success': success,
            'data': data if success else None,
        }
        
        # If it's an error, data usually contains the error details
        if not success:
            # DRF errors are often dicts or lists
            standardized_data['errors'] = data
            
            # If there's a 'message' or 'detail' in the error, extract it
            if isinstance(data, dict):
                if 'message' in data:
                    standardized_data['message'] = data.pop('message')
                elif 'detail' in data:
                    standardized_data['message'] = data.pop('detail')
        

        return super().render(standardized_data, accepted_media_type, renderer_context)
