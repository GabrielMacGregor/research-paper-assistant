const NAME_COLLATOR = new Intl.Collator("en", {
  sensitivity: "base",
  numeric: true
});

const compareNames = NAME_COLLATOR.compare.bind(NAME_COLLATOR);

export function normalizeId(value) {
  const id = Number(value);
  return Number.isFinite(id) ? id : null;
}

export function buildUsersById(users) {
  const usersById = new Map();

  if (!Array.isArray(users)) {
    return usersById;
  }

  for (let index = 0; index < users.length; index += 1) {
    const user = users[index];

    if (!user || typeof user !== "object") {
      continue;
    }

    const id = normalizeId(user.id);
    const name = typeof user.name === "string" ? user.name.trim() : "";

    if (id === null || !name) {
      continue;
    }

    usersById.set(id, {
      id,
      name
    });
  }

  return usersById;
}

export function buildFriendsMap(friends) {
  const friendsMap = new Map();

  if (!Array.isArray(friends)) {
    return friendsMap;
  }

  for (let index = 0; index < friends.length; index += 1) {
    const pair = friends[index];

    if (!Array.isArray(pair) || pair.length < 2) {
      continue;
    }

    const fromId = normalizeId(pair[0]);
    const toId = normalizeId(pair[1]);

    if (fromId === null || toId === null) {
      continue;
    }

    if (!friendsMap.has(fromId)) {
      friendsMap.set(fromId, new Set());
    }

    friendsMap.get(fromId).add(toId);
  }

  return friendsMap;
}

export function buildInterestsByUserId(interests) {
  const interestsByUserId = new Map();

  if (!interests || typeof interests !== "object" || Array.isArray(interests)) {
    return interestsByUserId;
  }

  const interestNames = Object.keys(interests);

  for (let interestIndex = 0; interestIndex < interestNames.length; interestIndex += 1) {
    const interestName = interestNames[interestIndex];
    const userIds = interests[interestName];

    if (!Array.isArray(userIds)) {
      continue;
    }

    for (let userIndex = 0; userIndex < userIds.length; userIndex += 1) {
      const userId = normalizeId(userIds[userIndex]);

      if (userId === null) {
        continue;
      }

      if (!interestsByUserId.has(userId)) {
        interestsByUserId.set(userId, new Set());
      }

      interestsByUserId.get(userId).add(interestName);
    }
  }

  return interestsByUserId;
}

export function buildEnrichedUsers(users, friendsMap, interestsByUserId) {
  const usersById = buildUsersById(users);
  const safeFriendsMap = friendsMap instanceof Map ? friendsMap : new Map();
  const safeInterestsByUserId = interestsByUserId instanceof Map ? interestsByUserId : new Map();
  const enrichedUsers = [];

  usersById.forEach(function (user) {
    const directFriends = safeFriendsMap.get(user.id) || new Set();
    const suggestedFriendIds = new Set();

    directFriends.forEach(function (friendId) {
      const friendsOfFriend = safeFriendsMap.get(friendId);

      if (!friendsOfFriend) {
        return;
      }

      friendsOfFriend.forEach(function (candidateId) {
        if (candidateId === user.id) {
          return;
        }

        if (directFriends.has(candidateId)) {
          return;
        }

        if (!usersById.has(candidateId)) {
          return;
        }

        suggestedFriendIds.add(candidateId);
      });
    });

    const ownInterests = safeInterestsByUserId.get(user.id) || new Set();
    const suggestedInterestsSet = new Set();

    directFriends.forEach(function (friendId) {
      const friendInterests = safeInterestsByUserId.get(friendId);

      if (!friendInterests) {
        return;
      }

      friendInterests.forEach(function (interest) {
        if (!ownInterests.has(interest)) {
          suggestedInterestsSet.add(interest);
        }
      });
    });

    enrichedUsers.push({
      id: user.id,
      name: user.name,
      suggestedFriends: Array.from(suggestedFriendIds)
        .map(function (friendId) {
          return usersById.get(friendId).name;
        })
        .sort(compareNames),
      suggestedInterests: Array.from(suggestedInterestsSet).sort(compareNames)
    });
  });

  return enrichedUsers;
}
