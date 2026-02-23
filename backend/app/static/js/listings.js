// Listings page: sort handler
document.addEventListener('DOMContentLoaded', () => {
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            const params = new URLSearchParams(window.location.search);
            params.set('sort', sortSelect.value);
            params.set('page', '1');
            window.location.search = params.toString();
        });
    }

    const filterForm = document.getElementById('filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(filterForm);
            const params = new URLSearchParams();
            for (const [key, value] of formData.entries()) {
                if (value) params.set(key, value);
            }
            const sortVal = document.getElementById('sort-select')?.value;
            if (sortVal) params.set('sort', sortVal);
            params.set('page', '1');
            window.location.search = params.toString();
        });
    }
});
