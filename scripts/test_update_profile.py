"""Offline regression tests for profile repository coverage."""
import unittest
from unittest.mock import patch

import update_profile as profile


class RepositoryScopeTests(unittest.TestCase):
    def test_pagination_excludes_private_but_keeps_forks(self):
        first = [{"id": i, "private": i == 1, "fork": i == 2} for i in range(100)]
        with patch.object(profile, "github", side_effect=[first, []]) as api:
            repos = profile.repositories("orgs/example/repos")
        self.assertEqual(len(repos), 99)
        self.assertIn(2, [repo["id"] for repo in repos])
        self.assertNotIn(1, [repo["id"] for repo in repos])
        self.assertEqual(api.call_count, 2)
        self.assertTrue(api.call_args.args[0].endswith("page=2"))

    def test_all_owned_organizations_and_repository_deduplication(self):
        personal = {"id": 1, "stargazers_count": 10}
        shared = {"id": 2, "stargazers_count": 5}
        cleanip = {"id": 3, "stargazers_count": 3}
        with patch.object(profile, "repositories", side_effect=[
            [personal], [shared], [cleanip, shared], [], []
        ]) as repositories:
            own, combined = profile.profile_repositories()
        self.assertEqual(own, [personal])
        self.assertEqual(sum(repo["stargazers_count"] for repo in combined), 18)
        self.assertEqual([call.args[0] for call in repositories.call_args_list], [
            "users/gentpan/repos", "orgs/QuotaBar/repos", "orgs/CleanIP/repos",
            "orgs/utterlog/repos", "orgs/ImgRouter/repos",
        ])


if __name__ == "__main__":
    unittest.main()
