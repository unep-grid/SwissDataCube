# Remove  "Don't have an account? Register here." from Login screen
In *data_cube_ui/apps/accounts/templates/registration/login.html*, comment the part:
```html
</form>
<!-- {% if form.errors %}
  <a style="" href="{% url 'lost_password' %}">{% trans "Forgot your username or password? Reset it here." %}</a>
{% endif %}
<a style="" href="{% url 'registration' %}">{% trans "Don't have an account? Register here." %}</a> -->
{% endblock %}
```
