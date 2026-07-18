<section class="card">

    <div class="card-header">
        <h2>Backup Plans</h2>
        <span class="badge">{{ backup_plans|length }}</span>
    </div>

    <div class="card-body">

        {% if backup_plans %}

        <table class="table">

            <thead>
                <tr>
                    <th>Application</th>
                    <th>Profile</th>
                    <th>Sources</th>
                    <th>Estimated Size</th>
                    <th>Warnings</th>
                    <th>Status</th>
                </tr>
            </thead>

            <tbody>

                {% for plan in backup_plans %}

                <tr>

                    <td>{{ plan.application }}</td>

                    <td>{{ plan.profile.name }}</td>

                    <td>{{ plan.sources|length }}</td>

                    <td>{{ plan.estimated_size }}</td>

                    <td>{{ plan.warnings|length }}</td>

                    <td>

                        {% if plan.ready %}

                        <span class="badge badge-success">
                            Ready
                        </span>

                        {% else %}

                        <span class="badge badge-warning">
                            Pending
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
                No backup plans have been generated yet.
            </p>

        </div>

        {% endif %}

    </div>

</section>