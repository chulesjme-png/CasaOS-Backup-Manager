<section class="card">

    <div class="card-header">
        <h2>Application Profiles</h2>
        <span class="badge">{{ application_profiles|length }}</span>
    </div>

    <div class="card-body">

        {% if application_profiles %}

        <table class="table">

            <thead>
                <tr>
                    <th>Name</th>
                    <th>Application</th>
                    <th>Description</th>
                    <th>Sources</th>
                    <th>Tags</th>
                    <th>Status</th>
                </tr>
            </thead>

            <tbody>

                {% for profile in application_profiles %}

                <tr>

                    <td>{{ profile.name }}</td>

                    <td>{{ profile.application }}</td>

                    <td>{{ profile.description }}</td>

                    <td>{{ profile.backup_sources|length }}</td>

                    <td>{{ profile.tags|join(", ") }}</td>

                    <td>

                        {% if profile.enabled %}
                        <span class="badge badge-success">
                            Enabled
                        </span>
                        {% else %}
                        <span class="badge badge-secondary">
                            Disabled
                        </span>
                        {% endif %}

                    </td>

                </tr>

                {% endfor %}

            </tbody>

        </table>

        {% else %}

        <div class="empty-state">

            <p>
                No application profiles have been generated yet.
            </p>

        </div>

        {% endif %}

    </div>

</section>